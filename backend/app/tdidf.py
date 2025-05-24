import joblib
import os
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re # Added import

class TfidfComparer:
    def __init__(self, model_path=None):
        if model_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_dir, '..', 'models', 'tfidf_vectorizer.joblib')
        
        try:
            self.vectorizer = joblib.load(model_path)
            print(f"TF-IDF model loaded successfully from {model_path}")
        except FileNotFoundError:
            print(f"Error: Model file not found at {model_path}. Please train the model first.")
            self.vectorizer = None
        except Exception as e:
            print(f"An error occurred while loading the model: {e}")
            self.vectorizer = None

    def _preprocess_text(self, text: str) -> str:
        # Consistent with preprocess_cyrillic in search.py and then lowercased
        # Remove all digits and non-cyrillic letters (except spaces), specific "арт" removal
        processed_text = re.sub(r'[^а-яА-ЯёЁ\s]', '', text)
        # Replace specific substring "арт" (article) if it exists
        processed_text = processed_text.replace('арт', "")
        # Collapse multiple spaces. Note: "a  b" -> "ab", "a   b" -> "a b" with str.replace("  ", "")
        # To be perfectly identical to search.py's preprocess_cyrillic's effect on spaces:
        while "  " in processed_text:
            processed_text = processed_text.replace("  ", "") # This was the original behavior in preprocess_cyrillic
        processed_text = processed_text.strip()
        return processed_text.lower()

    def compare_strings(self, text1: str, text2: str) -> float:
        """
        Compares two strings using the loaded TF-IDF model and cosine similarity.
        Returns a similarity score between 0 and 1.
        """
        if self.vectorizer is None:
            print("Error: TF-IDF vectorizer is not loaded. Cannot compare strings.")
            return 0.0

        processed_text1 = self._preprocess_text(text1)
        processed_text2 = self._preprocess_text(text2)

        # Transform the texts into TF-IDF vectors
        # The vectorizer expects a list of documents
        try:
            vector1 = self.vectorizer.transform([processed_text1])
            vector2 = self.vectorizer.transform([processed_text2])
        except Exception as e:
            print(f"Error transforming texts: {e}")
            return 0.0

        # Calculate cosine similarity
        # cosine_similarity returns a matrix, so we take the specific value
        similarity = cosine_similarity(vector1, vector2)[0][0]
        
        return similarity

    def get_similarity_scores(self, query_text: str, document_list: list[str]) -> list[tuple[str, float]]:
        """
        Compares a query string against a list of document strings.
        Returns a list of tuples, where each tuple contains the document and its similarity score 
        to the query_text, sorted by similarity in descending order.
        """
        if self.vectorizer is None:
            print("Error: TF-IDF vectorizer is not loaded. Cannot compute similarity scores.")
            return []

        if not document_list:
            return []

        processed_query = self._preprocess_text(query_text)
        processed_documents = [self._preprocess_text(doc) for doc in document_list]

        try:
            query_vector = self.vectorizer.transform([processed_query])
            document_vectors = self.vectorizer.transform(processed_documents)
        except Exception as e:
            print(f"Error transforming texts: {e}")
            return []
        
        # Calculate cosine similarities between the query vector and all document vectors
        similarities = cosine_similarity(query_vector, document_vectors)[0] # [0] because query_vector is 1xN

        # Pair documents with their scores
        scored_documents = list(zip(document_list, similarities))

        # Sort by similarity score in descending order
        scored_documents.sort(key=lambda x: x[1], reverse=True)

        return scored_documents


# if __name__ == '__main__':
#     # Example Usage:
#     comparer = TfidfComparer()

#     if comparer.vectorizer:
#         # Example strings - replace with your actual strings
#         string1 = "Пыльник Шруса Наружный"
#         string2 = "Пыльник шруса наружный для автомобиля хонда"
#         string3 = "Совершенно другой текст о кошках"
        
#         similarity12 = comparer.compare_strings(string1, string2)
#         print(f"Similarity between '{string1}' and '{string2}': {similarity12:.4f}")

#         similarity13 = comparer.compare_strings(string1, string3)
#         print(f"Similarity between '{string1}' and '{string3}': {similarity13:.4f}")

#         # Example with a list of documents
#         query = "автомобильный аккумулятор"
#         documents = [
#             "Аккумулятор для легкового автомобиля",
#             "Зарядное устройство для аккумулятора",
#             "Аккумуляторная батарея для грузовика",
#             "Клеммы для аккумулятора",
#             "Чехол на сиденье автомобиля"
#         ]
        
#         scores = comparer.get_similarity_scores(query, documents)
#         print(f"\nSimilarity scores for query '{query}':")
#         for doc, score in scores:
#             print(f"- '{doc}': {score:.4f}")

#         # Example with a non-existent word in vocabulary during training
#         # The TF-IDF vectorizer will ignore terms not seen during fit.
#         # This means if a string contains only new words, its vector might be all zeros.
#         string_new_vocab = "абвгд xyz qwerty" 
#         similarity_new_vocab = comparer.compare_strings(string1, string_new_vocab)
#         print(f"Similarity between '{string1}' and '{string_new_vocab}': {similarity_new_vocab:.4f}")

#         # Test with empty string
#         empty_string = ""
#         similarity_empty = comparer.compare_strings(string1, empty_string)
#         print(f"Similarity between '{string1}' and empty string: {similarity_empty:.4f}")
#         # Note: The behavior with empty strings or strings with only out-of-vocabulary words
#         # can lead to zero vectors, and cosine_similarity might produce nan or errors
#         # if not handled. Scikit-learn's TfidfVectorizer handles this gracefully by producing zero vectors.
#         # Cosine similarity between a non-zero vector and a zero vector is 0.
#         # Cosine similarity between two zero vectors is undefined (NaN), but sklearn handles it as 0.
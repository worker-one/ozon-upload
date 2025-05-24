import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

def load_corpus(file_path):
    corpus = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                corpus.append(line.strip())
    except FileNotFoundError:
        print(f"Error: Corpus file not found at {file_path}")
    return corpus

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_file_path = os.path.join(base_dir, '..', 'processed_data', 'corpus.txt')
    
    models_dir = os.path.join(base_dir, '..', 'models')
    model_path = os.path.join(models_dir, 'tfidf_vectorizer.joblib')

    # Create models directory if it doesn't exist
    os.makedirs(models_dir, exist_ok=True)

    corpus = load_corpus(corpus_file_path)

    if not corpus:
        print("Corpus is empty. Cannot train the model.")
        return

    print(f"Loaded {len(corpus)} documents from corpus.")

    # Initialize TF-IDF Vectorizer
    # You can customize parameters like stop_words, max_df, min_df, ngram_range etc.
    vectorizer = TfidfVectorizer()

    # Fit the vectorizer to the corpus
    print("Training TF-IDF model...")
    vectorizer.fit(corpus)
    print("TF-IDF model training complete.")

    # Save the trained vectorizer
    joblib.dump(vectorizer, model_path)
    print(f"Trained TF-IDF vectorizer saved to: {model_path}")

if __name__ == '__main__':
    main()

import requests

class AbcpClient:
    def __init__(self, base_url: str, userlogin: str, userpsw: str):
        self.userlogin = userlogin
        self.userpsw = userpsw
        self.base_url = base_url

    def search_by_number(self,  number: str, brand: str = None):
        url = f"{self.base_url}/search/brands/"
        params = {
            "userlogin": self.userlogin,
            "userpsw": self.userpsw,
            "number": number,
            "brand": brand
        }

        # Make the GET request
        response = requests.get(url, params=params)

        # Print the response
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = [data]
            return data
        else:
            return None
        
    def get_article_info(self, number: str, brand: str = None):
        url = f"{self.base_url}/articles/info/"
        params = {
            "userlogin": self.userlogin,
            "userpsw": self.userpsw,
            "number": number,
            "brand": brand,
            "cross_image": 1,
            "format": "bnpic",
        }

        # Make the GET request
        response = requests.get(url, params=params)

        # Print the response
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = [data]
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")

base_url = "http://abcp43533.public.api.abcp.ru"
image_base_url = "https://pubimg.nodacdn.net/images/"
userlogin = "api@10443826"
userpsw = "5a2cf962614e2a4f6c2f374047f387d9"
url = f"{base_url}/search/brands/"

abcp_client = AbcpClient(base_url, userlogin, userpsw)

number = "3149148"
brand = "LUKOIL"
result = abcp_client.search_by_number(number, brand)

if result:
    print("Search Results:")
    for item in result:
        print(item)
else:
    print("No results found or an error occurred.")
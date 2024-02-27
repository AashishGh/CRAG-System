import os
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from config import get_environment_config
import ssl
import certifi
from sentence_transformers import SentenceTransformer
import re
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_embedding(text):
    return model.encode(text).tolist()

def read_text_file(file_path):
    """Reads the content of a text file and splits it into title, abstract, and content."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    title = lines[0].strip()
    abstract = lines[1].strip()  # Assuming abstract is the second line; adjust if necessary
    content = " ".join(lines[2:]).strip()  # The rest is considered content
    return title, abstract, content

class ElasticRetrieval:
    def __init__(self, connection_string,username,password):
       # Create a default SSL context
        context = ssl.create_default_context()
        # Optionally disable verification for development
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        print("***************",username,password)
        
        connection_string_with_auth = f"https://{username}:{password}@{connection_string.lstrip('https://')}"
        
        self.es = Elasticsearch(
            connection_string_with_auth,
            ssl_context=context,
            # use_ssl=True,
            verify_certs=False,
            # scheme="https"
            # Other configurations as before
        )  
        print("CONNECTION ELSTABLISHED WITH ELASTIC SEARCH")

    def preprocess_content(self, content):
        # Example regex patterns for metadata (customize these!)
        patterns_to_remove = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+, [A-Z][a-z]+ [A-Z][a-z]+, .+?\b',  # Names followed by affiliations
            r'Manuscript Author',  # Specific phrases
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
            r'HHS Public Access',  # Specific header/footer phrases
            # Add more patterns as needed
        ]

        # Loop over each pattern and remove matches from the content
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content)

        # Optional: Additional cleaning steps (e.g., removing extra whitespace)
        content = re.sub(r'\s+', ' ', content).strip()

        return content
    
    def create_index(self, index_name):
        """Creates an index with specific settings for text content."""
        index_settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "title": {"type": "text"},
                "abstract": {"type": "text"},
                "content": {"type": "text"},
                "vector": {
                    "type": "dense_vector",
                    "dims": 384  # Adjust based on your embedding dimensionality
                }
            }
        }
        }
        try:
            self.es.indices.create(index=index_name, body=index_settings)
            print(f"Index '{index_name}' created successfully.")
        except Exception as e:
            if "resource_already_exists_exception" in str(e):
                print(f"Index '{index_name}' already exists.")
            else:
                raise

    def index_documents(self, directory_path, index_name):
        self.create_index(index_name)
        files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
        actions = []
        for file in files:
            file_path = os.path.join(directory_path, file)
            title, abstract, content = read_text_file(file_path)
            
            # Preprocess content to remove or separate metadata
            cleaned_content = self.preprocess_content(content)
            
            # Generate embedding for the cleaned content
            vector = generate_embedding(cleaned_content)
            doc = {
                '_op_type': 'index',
                '_index': index_name,
                '_source': {
                    'title': title,
                    'abstract': abstract,
                    'content': cleaned_content,
                    'vector': vector  # Add the vector to the document source
                }
            }
            actions.append(doc)
        
        if actions:
            bulk(self.es, actions)
            print(f"Indexed {len(actions)} documents to '{index_name}'.")

            
    def get_indices(self):
        try:
            # Retrieve all indices
            all_indices = self.es.indices.get_alias().keys()
            # Filter out system indices (those starting with '.')
            user_indices = [index for index in all_indices if not index.startswith('.')]
            # Sort indices for better readability
            user_indices.sort()
            return user_indices
        except Exception as e:
            print(f"Error retrieving indices: {e}")
            return []
    

    def search_documents(self, query, index_name, top_k=3):
        query_vector = generate_embedding(query)  # Generate the query vector
        script_query = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {"query_vector": query_vector}
                    }
                }
            }
        }
        response = self.es.search(index=index_name, body=script_query)
        return [hit["_source"]["content"] for hit in response['hits']['hits']]

   

    def delete_index(self, index_name):
        """Deletes the specified index."""
        try:
            response = self.es.indices.delete(index=index_name)
            print(f"Index '{index_name}' was deleted successfully.")
            return response
        except Exception as e:
            print(f"Error deleting index '{index_name}': {e}")

def get_elastic_retrieval_obj():
    """Function to instantiate and return an ElasticRetrieval object with the configured connection string."""
    elastic_conn_str = get_environment_config('ELASTIC_CONNECTION_URL')
    username = get_environment_config('ELASTIC_USERNAME')
    password = get_environment_config('ELASTIC_PASSWORD')
    return ElasticRetrieval(connection_string=elastic_conn_str, username=username, password=password)


def create_elastic_index_func(elastic_retrieval,subdir_list=os.listdir('./documents')):
    base_dir = "./documents"  # Adjust as needed
    # for subdir in os.listdir(base_dir):
    for subdir in subdir_list:
        if os.path.isdir(os.path.join(base_dir, subdir)):
            index_name = subdir.lower()  # Using the directory name as the index name, converted to lowercase
            directory_path = os.path.join(base_dir, subdir)
            elastic_retrieval.index_documents(directory_path=directory_path, index_name=index_name)



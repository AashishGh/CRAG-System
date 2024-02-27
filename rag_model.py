import os
import openai
from transformers import GPT2Tokenizer, GPT2LMHeadModel, pipeline
from elastic import get_elastic_retrieval_obj  # Make sure this function exists
from config import get_environment_config  # Assuming this fetches necessary configurations
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RAGModel:
    def __init__(self):
        self.api_key = get_environment_config('OPEN_API_KEY')
        self.model_name = get_environment_config("OPEN_API_MODEL")
        self.elastic_retrieval = get_elastic_retrieval_obj()
        self.tokenizer = GPT2Tokenizer.from_pretrained(self.model_name)
        self.model = GPT2LMHeadModel.from_pretrained(self.model_name)
        # Initialize a summarizer pipeline for document summarization
        self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

    def get_indices_from_elasticsearch(self):
        return self.elastic_retrieval.get_indices()


    def search_and_summarize_documents(self, query):
        indices = self.get_indices_from_elasticsearch()
        summarized_docs = []
        for index in indices:
            docs = self.elastic_retrieval.search_documents(query, index_name=index)
            for doc in docs:
                # Attempt to summarize each document
                try:
                    # Ensure the document is within a reasonable length; if not, truncate or split.
                    if len(doc) > 1024:  # Example check for length; adjust based on your tokenizer
                        doc = doc[:1024]  # Simple truncation; consider smarter splitting
                    
                    summary_output = self.summarizer(doc, max_length=100, min_length=25, do_sample=False)
                    if summary_output and len(summary_output) > 0 and 'summary_text' in summary_output[0]:
                        summary = summary_output[0]['summary_text']
                        summarized_docs.append(summary)
                    else:
                        summarized_docs.append("Document couldn't be summarized due to an error.")
                except Exception as e:
                    print(f"Error summarizing document: {e}")
                    summarized_docs.append("Document couldn't be summarized due to an error.")
        return summarized_docs
    def extract_key_information(self, document):
        # Placeholder for a method to extract key sentences or phrases from the document
        # This is a simplified example; you might need a more sophisticated approach
        sentences = document.split('. ')
        key_sentences = sentences[:2]  # Naively take the first two sentences
        return ' '.join(key_sentences)
        
    def search_documents(self,query):
        indices = self.get_indices_from_elasticsearch()
        extracted_info = []
        for index in indices:
            docs = self.elastic_retrieval.search_documents(query, index_name=index)
            for doc in docs:
                # Extract key information from each document
                info = self.extract_key_information(doc)
                extracted_info.append(info)
        return extracted_info


    def refine_context(self, documents):
        refined_context = []
        for doc in documents:
            # Here you can implement more sophisticated logic to refine context
            # This example just simplifies the context generation
            content_sentences = doc.split('. ')[:2]  # Simplistically take the first 2 sentences
            refined_context.extend(content_sentences)
        return " ".join(refined_context)

    def generate_response(self, query):
        # documents = self.search_and_summarize_documents(query)
        documents=self.search_documents(query)   
        print("LEngth: ******",len(documents))
        refined_context = self.refine_context(documents)  # Use the refined context for response generation
        # input_text = f"Question: {query} Context: {refined_context}"
        input_text = f"Context: {refined_context}\nQuestion: {query}\nAnswer:"

        input_ids = self.tokenizer.encode(input_text, truncation=True, max_length=1024, return_tensors='pt')
        
        try:
            output_ids = self.model.generate(input_ids,max_new_tokens=1, pad_token_id=self.tokenizer.eos_token_id)
            response = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        except Exception as e:
            print(f"Error during response generation: {e}")
            response = "I'm sorry, I couldn't generate a response based on the information provided."
        # Extract the generated answer from the response. This assumes the "Answer:" part is at the end of the input_text.
        answer_start = response.find("Answer:") + len("Answer:")
        answer = response[answer_start:].strip()
        # print("Response:\n",response)
        return answer,query

def main():
    rag_model = RAGModel()
    question = "What is the significance of biofilms in this technological world?"
    response = rag_model.generate_response(question)
    print("\n *************Response is:**********\n", response)

if __name__ == "__main__":
    main()

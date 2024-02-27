from elastic import get_elastic_retrieval_obj, create_elastic_index_func
elastic_retrieval= get_elastic_retrieval_obj()


create_elastic_index_func(elastic_retrieval)
    
indices=elastic_retrieval.get_indices()
print("INDEX:", indices)
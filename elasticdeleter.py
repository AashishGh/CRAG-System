from elastic import get_elastic_retrieval_obj
elastic_retrieval= get_elastic_retrieval_obj()

indices_to_delete=['biofilms','material','microbe']
for index_to_delete in indices_to_delete:
    elastic_retrieval.delete_index(index_to_delete)

indices=elastic_retrieval.get_indices()
print("INDEX:", indices)
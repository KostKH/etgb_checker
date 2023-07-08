from db_layer.database import QueryRepository, ResultsRepository

if __name__ == '__main__':
    query_rep = QueryRepository()
    results_rep = ResultsRepository()
    results_rep.create_table()
    query_rep.create_table()

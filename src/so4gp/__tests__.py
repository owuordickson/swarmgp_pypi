import pandas
import TemporalGP.so4gp as sgp

if __name__ == "__main__":

    dummy_data = [[30, 3, 1, 10], [35, 2, 2, 8], [40, 4, 2, 7], [50, 1, 1, 6], [52, 7, 1, 2]]
    dummy_df = pandas.DataFrame(dummy_data, columns=['Age', 'Salary', 'Cars', 'Expenses'])
    mine_obj = sgp.GRAANK(data_source=dummy_df, min_sup=0.5, eq=False)
    result_json = mine_obj.discover()
    print(result_json)
# -*- coding: utf-8 -*-
"""
@author: "Dickson Owuor"
@credits: "Thomas Runkler, Edmond Menya, and Anne Laurent,"
@license: "MIT"
@version: "4.0"
@email: "owuordickson@gmail.com"
@created: "12 July 2019"
@modified: "21 Jul 2021"

Breath-First Search for gradual patterns (ACO-GRAANK)

Modification: generates distance matrix (d_matrix)

"""
import numpy as np
from gp import GI, GP
from dataset_bfs import Dataset
import config as cfg


class acogp:

    @staticmethod
    def generate_d(valid_bins):
        v_bins = valid_bins
        # 1. Fetch valid bins group
        attr_keys = [GI(x[0], x[1].decode()).as_string() for x in v_bins[:, 0]]

        # 2. Initialize an empty d-matrix
        n = len(attr_keys)
        d = np.zeros((n, n), dtype=np.dtype('i8'))  # cumulative sum of all segments
        for i in range(n):
            for j in range(n):
                if GI.parse_gi(attr_keys[i]).attribute_col == GI.parse_gi(attr_keys[j]).attribute_col:
                    # Ignore similar attributes (+ or/and -)
                    continue
                else:
                    bin_1 = v_bins[i][1]
                    bin_2 = v_bins[j][1]
                    # Cumulative sum of all segments for 2x2 (all attributes) gradual items
                    d[i][j] += np.sum(np.multiply(bin_1, bin_2))
        # print(d)
        return d, attr_keys

    @staticmethod
    def run_ant_colony(f_path, min_supp=cfg.MIN_SUPPORT, evaporation_factor=cfg.EVAPORATION_FACTOR, max_iteration=cfg.MAX_ITERATIONS):

        # 0. Initialize and prepare data set
        d_set = Dataset(f_path, min_supp)
        d_set.init_gp_attributes()
        # attr_index = d_set.attr_cols
        # e_factor = evaporation_factor
        d, attr_keys = acogp.generate_d(d_set.valid_bins)  # distance matrix (d) & attributes corresponding to d

        a = d_set.attr_size
        winner_gps = list()  # subsets
        loser_gps = list()  # supersets
        str_winner_gps = list()  # subsets
        repeated = 0
        it_count = 0
        max_it = max_iteration

        if d_set.no_bins:
            return []

        # 1. Remove d[i][j] < frequency-count of min_supp
        fr_count = ((min_supp * a * (a - 1)) / 2)
        d[d < fr_count] = 0

        # 2. Calculating the visibility of the next city
        # visibility(i,j)=1/d(i,j)
        # In the case GP mining visibility = d
        # with np.errstate(divide='ignore'):
        #    visibility = 1/d
        #    visibility[visibility == np.inf] = 0

        # 3. Initialize pheromones (p_matrix)
        pheromones = np.ones(d.shape, dtype=float)

        # 4. Iterations for ACO
        # while repeated < 1:
        while it_count < max_it:
            rand_gp, pheromones = acogp.generate_aco_gp(attr_keys, d, pheromones, evaporation_factor)
            if len(rand_gp.gradual_items) > 1:
                # print(rand_gp.get_pattern())
                exits = acogp.is_duplicate(rand_gp, winner_gps, loser_gps)
                if not exits:
                    repeated = 0
                    # check for anti-monotony
                    is_super = acogp.check_anti_monotony(loser_gps, rand_gp, subset=False)
                    is_sub = acogp.check_anti_monotony(winner_gps, rand_gp, subset=True)
                    if is_super or is_sub:
                        continue
                    gen_gp = acogp.validate_gp(d_set, rand_gp)
                    is_present = acogp.is_duplicate(gen_gp, winner_gps, loser_gps)
                    is_sub = acogp.check_anti_monotony(winner_gps, gen_gp, subset=True)
                    if is_present or is_sub:
                        repeated += 1
                    else:
                        if gen_gp.support >= min_supp:
                            pheromones = acogp.update_pheromones(attr_keys, gen_gp, pheromones)
                            winner_gps.append(gen_gp)
                            str_winner_gps.append(gen_gp.print(d_set.titles))
                        else:
                            loser_gps.append(gen_gp)
                    if set(gen_gp.get_pattern()) != set(rand_gp.get_pattern()):
                        loser_gps.append(rand_gp)
                else:
                    repeated += 1
            it_count += 1

        # Output
        out = {'Best Patterns': str_winner_gps, 'Iterations': it_count}

        return out

    @staticmethod
    def generate_aco_gp(attr_keys, d, p_matrix, e_factor):
        v_matrix = d
        pattern = GP()

        # 1. Generate gradual items with highest pheromone and visibility
        m = p_matrix.shape[0]
        for i in range(m):
            combine_feature = np.multiply(v_matrix[i], p_matrix[i])
            total = np.sum(combine_feature)
            with np.errstate(divide='ignore', invalid='ignore'):
                probability = combine_feature / total
            cum_prob = np.cumsum(probability)
            r = np.random.random_sample()
            try:
                j = np.nonzero(cum_prob > r)[0][0]
                gi = GI.parse_gi(attr_keys[j])
                if not pattern.contains_attr(gi):
                    pattern.add_gradual_item(gi)
            except IndexError:
                continue

        # 2. Evaporate pheromones by factor e
        p_matrix = (1 - e_factor) * p_matrix
        return pattern, p_matrix

    @staticmethod
    def update_pheromones(attr_keys, pattern, p_matrix):
        idx = [attr_keys.index(x.as_string()) for x in pattern.gradual_items]
        for n in range(len(idx)):
            for m in range(n + 1, len(idx)):
                i = idx[n]
                j = idx[m]
                p_matrix[i][j] += 1
                p_matrix[j][i] += 1
        return p_matrix

    @staticmethod
    def validate_gp(d_set, pattern):
        # pattern = [('2', '+'), ('4', '+')]
        min_supp = d_set.thd_supp
        n = d_set.attr_size
        gen_pattern = GP()
        bin_arr = np.array([])

        for gi in pattern.gradual_items:
            arg = np.argwhere(np.isin(d_set.valid_bins[:, 0], gi.gradual_item))
            if len(arg) > 0:
                i = arg[0][0]
                valid_bin = d_set.valid_bins[i]
                if bin_arr.size <= 0:
                    bin_arr = np.array([valid_bin[1], valid_bin[1]])
                    gen_pattern.add_gradual_item(gi)
                else:
                    bin_arr[1] = valid_bin[1].copy()
                    temp_bin = np.multiply(bin_arr[0], bin_arr[1])
                    supp = float(np.sum(temp_bin)) / float(n * (n - 1.0) / 2.0)
                    if supp >= min_supp:
                        bin_arr[0] = temp_bin.copy()
                        gen_pattern.add_gradual_item(gi)
                        gen_pattern.set_support(supp)
        if len(gen_pattern.gradual_items) <= 1:
            return pattern
        else:
            return gen_pattern

    @staticmethod
    def check_anti_monotony(lst_p, pattern, subset=True):
        result = False
        if subset:
            for pat in lst_p:
                result1 = set(pattern.get_pattern()).issubset(set(pat.get_pattern()))
                result2 = set(pattern.inv_pattern()).issubset(set(pat.get_pattern()))
                if result1 or result2:
                    result = True
                    break
        else:
            for pat in lst_p:
                result1 = set(pattern.get_pattern()).issuperset(set(pat.get_pattern()))
                result2 = set(pattern.inv_pattern()).issuperset(set(pat.get_pattern()))
                if result1 or result2:
                    result = True
                    break
        return result

    @staticmethod
    def is_duplicate(pattern, lst_winners, lst_losers):
        for pat in lst_losers:
            if set(pattern.get_pattern()) == set(pat.get_pattern()) or \
                    set(pattern.inv_pattern()) == set(pat.get_pattern()):
                return True
        for pat in lst_winners:
            if set(pattern.get_pattern()) == set(pat.get_pattern()) or \
                    set(pattern.inv_pattern()) == set(pat.get_pattern()):
                return True
        return False

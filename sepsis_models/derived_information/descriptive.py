def calculate_feature_rates(df, source_row=None, min_rate=0.01, max_rate=None):
    feature_rates = {
        (feature_name, v): count
        for feature_name in df.columns
        if feature_name not in ('id', 'intime')
        for v, count in df[feature_name].value_counts().items()
        if source_row is None or v == source_row[feature_name]
    }
    feature_rates = {
        (feature_name, k): v for (feature_name, k), v in feature_rates.items()
        if not feature_name.endswith("Present") and k not in ('Missing', 'Missing/Normal')
        if v / len(df) >= min_rate and (max_rate is None or v / len(df) < max_rate)
    }
    return feature_rates

class DescriptiveInformation:
    """
    Generates information for an instance about what features are most similar to 
    its nearest neighbors compared to the dataset, and what features are most
    unusual within its nearest neighbors.
    """
    def __init__(self, train_states, min_rate=0.01):
        self.train_states = train_states
        self.feature_base_rates = calculate_feature_rates(self.train_states, max_rate=0.5, min_rate=min_rate)

    def get_most_similar_features(self, indexes, source_row, k=3):
        """
        :param indexes: the indexes of the nearest neighbors to the source row
            in the training set
        :param source_row: a pandas Series (dataframe row) containing the feature
            values of the instance of interest
        :param k: the maximum number of feature values to return
        """
        selection_feature_rates = calculate_feature_rates(self.train_states.iloc[indexes], source_row=source_row, min_rate=0.7)
        selection_feature_rates = {k: v for k, v in selection_feature_rates.items()
                                if k in self.feature_base_rates}
        return [
            {
                'feature': feature_name, 
                'value': value,
                'base_rate': '{:d}%'.format(round(self.feature_base_rates[(feature_name, value)] / len(self.train_states) * 100)),
                'group_rate': '{:d}%'.format(round(selection_feature_rates[(feature_name, value)] / len(indexes) * 100))
            }
            for (feature_name, value) in sorted(selection_feature_rates.keys(),
                                                key=lambda x: (selection_feature_rates[x] / len(indexes)) /
                                                ((self.feature_base_rates[x] - selection_feature_rates[x]) / (len(self.train_states) - len(indexes))),
                                                reverse=True)[:k]
        ]

    def get_most_different_features(self, indexes, source_row, k=3):
        """
        :param indexes: the indexes of the nearest neighbors to the source row
            in the training set
        :param source_row: a pandas Series (dataframe row) containing the feature
            values of the instance of interest
        :param k: the maximum number of feature values to return
        """
        selection_feature_rates = calculate_feature_rates(self.train_states.iloc[indexes], source_row=source_row, max_rate=0.2)
        selection_feature_rates = {k: v for k, v in selection_feature_rates.items()
                                if k in self.feature_base_rates}
        matching_feature_rates = {(c, source_row[c]): (self.feature_base_rates[(c, source_row[c])] / selection_feature_rates[(c, source_row[c])]) for c in source_row.index
                                if (c, source_row[c]) in selection_feature_rates}
        return [
            {
                'feature': feature_name, 
                'value': value,
                'group_rate': '{:d}%'.format(round(selection_feature_rates[(feature_name, value)] / len(indexes) * 100)),
                'base_rate': '{:d}%'.format(round(self.feature_base_rates[(feature_name, value)] / len(self.train_states) * 100)),
            }
            for (feature_name, value) in sorted(matching_feature_rates.keys(),
                                                key=matching_feature_rates.get, reverse=True)[:k]
        ]
import time
import warnings
import pandas as pd
from collections import Counter
from IPython.display import display

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB

from sklearn.model_selection import cross_val_predict
from sklearn.base import clone
from sklearn.metrics import f1_score, recall_score, precision_score, roc_auc_score, accuracy_score

from catboost import CatBoostClassifier
from xgboost import XGBClassifier

from exerevnetes.utils import time_format


default_classifiers = {
    "random_forest": RandomForestClassifier(n_jobs=-1),
    "extra_tree": ExtraTreesClassifier(n_jobs=-1),
    "logistic_reg": LogisticRegression(),
    "svc": SVC(),
    "catboost": CatBoostClassifier(verbose=False, allow_writing_files=False),
    "xgboost": XGBClassifier(),
    "naive_bayes": GaussianNB()
}

default_metric_funcs = [
    f1_score,
    recall_score,
    precision_score,
    roc_auc_score,
    accuracy_score
]

class BinaryClassifierComparator:
    def __init__(self, X, y, classifiers: dict = default_classifiers, cv=5, metric_funcs: list = default_metric_funcs, pipeline=None):
        self.X = X
        self.n_classes = len(Counter(y))
        if self.n_classes != 2:
            raise ValueError(f"Expected 2 classes but got {self.n_classes}.")
        self.y = y
        self.classifiers = classifiers
        self.cv = cv
        self.metric_funcs = metric_funcs
        self.pipeline = pipeline
        self._metrics = {}
        if pipeline:
            self.__build_pipelines(pipeline)
    
    def run(self):
        print(f"The comparator has started...\nRunning for {len(self.classifiers)} classifiers")
        initial_time = time.time()
        for i, (clf_name, clf) in enumerate(self.classifiers.items()):
            print(f"Running cross validation for {i+1}. {clf_name}...", end="")
            clf_time = time.time()
            preds = cross_val_predict(clf, self.X, self.y, cv=self.cv)
            cv_time = time.time() - clf_time
            self._metrics[clf_name] = {"cv_time": cv_time}
            print((15 - len(clf_name))*" ",f"training time: {time_format(cv_time)}")
            self.__calculate_scores(clf_name, preds)

        # print times and metrics
        print(f"Total comparator time {time_format(time.time() - initial_time)}")
        self.__format_metrics()
        display(self._metrics)

    def __calculate_scores(self, clf_name, preds):
        for m in self.metric_funcs:
            self._metrics[clf_name][m.__name__] = m(self.y, preds)

    def __format_metrics(self):
        self._metrics = pd.DataFrame(self._metrics).T

    def __build_pipelines(self, pipeline):
        for clf_name, clf in self.classifiers.items():
            tmp_pipe = clone(pipeline)
            tmp_pipe.steps.append(("model", clf))
            self.classifiers[clf_name] = tmp_pipe

    def get_metrics(self):
        assert(len(self._metrics) != 0), "There are no metrics to be shown, you need to run the comparator first."
        return self._metrics
    
    def get_pipeline(self):
        if not self.pipeline:
            warnings.warn("The pipeline attribute is \033[1mNone\033[m and has not been defined.", UserWarning)
        return self.pipeline

    def best_clf(self, metric="f1_score"):
        assert(len(self._metrics) != 0), "There are no models to compare, you need to run the comparator first."
        if self.pipeline:
            return self.classifiers[self._metrics.sort_values(by=metric).index[-1]].steps[-1][1]
        else:
            return self.classifiers[self._metrics.sort_values(by=metric).index[-1]]
"""
Small PyTorch helpers for the classifiers in the analysis notebooks.

The same code used to be copied into every notebook. It is kept here once:
  split_data()        60 % train / 20 % cross-validation / 20 % test
  make_model()        fully connected network with ReLU layers and one output logit
  train_classifier()  mini-batch training with Adam and binary cross-entropy
  predict()           0/1 predictions
  report()            accuracy, majority-class baseline, confusion matrix, per-class scores
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


def split_data(X, y, seed=1):
    """Split into 60 % training, 20 % cross-validation and 20 % test data.

    Returns a dict with X_train, y_train, X_cv, y_cv, X_test, y_test (pandas objects).
    """
    X_train, X_rest, y_train, y_rest = train_test_split(X, y, test_size=0.40, random_state=seed)
    X_cv, X_test, y_cv, y_test = train_test_split(X_rest, y_rest, test_size=0.50, random_state=seed)
    return dict(X_train=X_train, y_train=y_train, X_cv=X_cv, y_cv=y_cv, X_test=X_test, y_test=y_test)


def to_tensor(data):
    """pandas/NumPy -> float32 tensor; a 1-D target becomes a column of shape (rows, 1)."""
    t = torch.tensor(np.asarray(data, dtype=np.float32))
    return t.reshape(-1, 1) if t.ndim == 1 else t


def make_model(n_inputs, hidden=(32, 16)):
    """Network: n_inputs -> hidden layers with ReLU -> 1 logit (the loss applies the sigmoid)."""
    layers, n = [], n_inputs
    for h in hidden:
        layers += [nn.Linear(n, h), nn.ReLU()]
        n = h
    layers.append(nn.Linear(n, 1))
    return nn.Sequential(*layers)


def train_classifier(model, X_train, y_train, X_cv, y_cv, *, epochs=300, batch_size=100, lr=0.01, seed=1):
    """Train `model` and return the loss history {'loss': [...], 'val_loss': [...]} (one value per epoch).

    The batch order is reproducible (fixed by `seed`). For reproducible initial weights, call
    torch.manual_seed(...) before make_model(), as the notebooks do.
    """
    Xtr, ytr, Xcv, ycv = to_tensor(X_train), to_tensor(y_train), to_tensor(X_cv), to_tensor(y_cv)
    loss_fn = nn.BCEWithLogitsLoss()                        # binary cross-entropy that takes logits
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    generator = torch.Generator().manual_seed(seed)         # reproducible shuffling
    history = {'loss': [], 'val_loss': []}

    for _ in range(epochs):
        order = torch.randperm(len(Xtr), generator=generator)   # new random order every epoch
        for start in range(0, len(Xtr), batch_size):
            idx = order[start:start + batch_size]
            optimizer.zero_grad()                 # clear the gradients of the previous batch
            loss = loss_fn(model(Xtr[idx]), ytr[idx])
            loss.backward()                       # back-propagation
            optimizer.step()                      # update the weights
        with torch.no_grad():                     # loss on the full sets, for the learning curves
            history['loss'].append(loss_fn(model(Xtr), ytr).item())
            history['val_loss'].append(loss_fn(model(Xcv), ycv).item())
    return history


def predict(model, X):
    """0/1 predictions (probability > 0.5) as a 1-D NumPy array."""
    with torch.no_grad():
        return (torch.sigmoid(model(to_tensor(X))) > 0.5).numpy().astype(int).ravel()


def accuracy(model, X, y):
    return accuracy_score(np.asarray(y).astype(int), predict(model, X))


def majority_baseline(y):
    """Accuracy of always predicting the most frequent class - the number a classifier has to beat."""
    share = float(np.mean(np.asarray(y).astype(int)))
    return max(share, 1 - share)


def summary_table(models, data):
    """Accuracy of several models on the training and cross-validation sets, next to the baseline.

    models: {name: model}; data: the dict returned by split_data().
    """
    rows = [{'model': name,
             'train accuracy': accuracy(m, data['X_train'], data['y_train']),
             'CV accuracy': accuracy(m, data['X_cv'], data['y_cv']),
             'majority baseline (CV)': majority_baseline(data['y_cv'])} for name, m in models.items()]
    return pd.DataFrame(rows).set_index('model').round(3)


def report(model, X, y, title=''):
    """Print the confusion matrix (rows = true class, columns = predicted) and per-class scores."""
    y_true, y_pred = np.asarray(y).astype(int), predict(model, X)
    print(f'{title}: accuracy {accuracy_score(y_true, y_pred):.3f} (majority baseline {majority_baseline(y_true):.3f})')
    print('confusion matrix [rows: true 0/1, columns: predicted 0/1]')
    print(confusion_matrix(y_true, y_pred, labels=[0, 1]))
    print(classification_report(y_true, y_pred, labels=[0, 1], digits=3, zero_division=0))


def error_table(model, X, y):
    """Median feature values of the correct predictions, false positives and false negatives."""
    y_true, y_pred = np.asarray(y).astype(int), predict(model, X)
    kind = np.where(y_pred == y_true, 'correct', np.where(y_pred == 1, 'false positive', 'false negative'))
    table = pd.DataFrame(X).groupby(kind).median().T
    table.loc['number of runs'] = pd.Series(kind).value_counts()
    return table

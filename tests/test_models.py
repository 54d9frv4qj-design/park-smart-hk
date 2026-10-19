# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 機器學習模型測試
"""
import pytest
import pandas as pd
import numpy as np

# xgboost / lightgbm 屬可選重型依賴，缺失時整個模型測試模組跳過
pytest.importorskip("xgboost")
pytest.importorskip("lightgbm")

from src.models.feature_engineering import build_features, get_feature_columns
from src.models.target_encoding import TargetEncoder
from src.models.xgboost_model import XGBoostClassifier
from src.models.lightgbm_model import LightGBMRegressor
from src.models.evaluate import evaluate_regressor, evaluate_classifier


class TestFeatureEngineering:
    """特徵工程測試"""

    def test_build_features(self):
        """測試特徵構建"""
        # 構造簡單測試數據
        dates = pd.date_range("2026-10-01", periods=20, freq="15min")
        df = pd.DataFrame({
            "park_id": ["P1"] * 20,
            "snapshot_time": dates,
            "vacancy": np.random.randint(0, 100, 20),
            "total_spaces": [100] * 20,
        })
        result = build_features(df)
        assert "hour" in result.columns
        assert "day_of_week" in result.columns
        assert "lag_1" in result.columns
        assert "rolling_mean_4" in result.columns
        assert len(result) > 0

    def test_get_feature_columns(self):
        """測試特徵列名"""
        features = get_feature_columns()
        assert "hour" in features
        assert "lag_1" in features
        assert len(features) > 10


class TestTargetEncoder:
    """Target Encoding 測試"""

    def test_fit_transform(self):
        """測試擬合與轉換"""
        df = pd.DataFrame({
            "park_id": ["A", "A", "B", "B", "C"],
            "target": [1, 0, 1, 1, 0],
        })
        encoder = TargetEncoder(smoothing=5.0)
        result = encoder.fit_transform(df, "park_id", "target")
        assert "park_id_te" in result.columns
        assert encoder.is_fitted_

    def test_transform_unseen(self):
        """測試未見過的類別"""
        df = pd.DataFrame({"park_id": ["A", "B"], "target": [1, 0]})
        encoder = TargetEncoder().fit(df, "park_id", "target")
        new_df = pd.DataFrame({"park_id": ["A", "Z"]})  # Z 未見過
        result = encoder.transform(new_df, "park_id")
        assert result.loc[1, "park_id_te"] == encoder.global_mean_


class TestXGBoostClassifier:
    """XGBoost 分類模型測試"""

    def test_train_predict(self):
        """測試訓練與預測"""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "hour": np.random.randint(0, 24, n),
            "day_of_week": np.random.randint(0, 7, n),
            "lag_1": np.random.randint(0, 100, n),
            "total_spaces": [100] * n,
            "target_class_4": np.random.randint(0, 2, n),
        })
        model = XGBoostClassifier(horizon=30)
        model.fit(df, target_col="target_class_4")
        assert model.is_fitted

        # 預測
        X = df[["hour", "day_of_week", "lag_1", "total_spaces"]]
        preds = model.predict(X)
        assert len(preds) == n
        assert set(preds).issubset({0, 1})


class TestLightGBMRegressor:
    """LightGBM 回歸模型測試"""

    def test_train_predict(self):
        """測試訓練與預測"""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "hour": np.random.randint(0, 24, n),
            "day_of_week": np.random.randint(0, 7, n),
            "lag_1": np.random.randint(0, 100, n),
            "total_spaces": [100] * n,
            "target_4": np.random.randint(0, 100, n),
        })
        model = LightGBMRegressor(horizon=30)
        model.fit(df, target_col="target_4")
        assert model.is_fitted

        X = df[["hour", "day_of_week", "lag_1", "total_spaces"]]
        preds = model.predict(X)
        assert len(preds) == n
        assert all(p >= 0 for p in preds)  # 空位不能為負


class TestEvaluation:
    """模型評估測試"""

    def test_evaluate_regressor(self):
        """測試回歸評估"""
        y_true = np.array([10, 20, 30, 40, 50])
        y_pred = np.array([12, 18, 33, 38, 52])
        result = evaluate_regressor(y_true, y_pred, "test")
        assert "MAE" in result
        assert "RMSE" in result
        assert result["MAE"] >= 0

    def test_evaluate_classifier(self):
        """測試分類評估"""
        y_true = np.array([0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 0, 1])
        result = evaluate_classifier(y_true, y_pred, model_name="test")
        assert "accuracy" in result
        assert "F1" in result
        assert 0 <= result["accuracy"] <= 1

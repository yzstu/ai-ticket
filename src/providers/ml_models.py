"""
机器学习和深度学习模型实现
提供实际的股票预测模型
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import joblib
import warnings
warnings.filterwarnings('ignore')

# Scikit-learn
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score

# XGBoost
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("XGBoost not available, install with: pip install xgboost")

# Keras
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import GRU, LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    HAS_KERAS = True
except ImportError:
    HAS_KERAS = False
    print("TensorFlow not available, install with: pip install tensorflow")

class XGBoostTrendPredictor:
    """XGBoost趋势预测模型"""

    def __init__(self):
        """初始化XGBoost模型"""
        if not HAS_XGBOOST:
            self.model = None
            self.scaler = None
            return

        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=100,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False

    def prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """
        准备特征数据

        Args:
            data: 股票数据DataFrame

        Returns:
            特征矩阵
        """
        features = []

        # 技术指标特征
        if 'rsi' in data.columns:
            features.append(data['rsi'].values)

        if 'macd_histogram' in data.columns:
            features.append(data['macd_histogram'].values)

        if 'ma5' in data.columns and 'close' in data.columns:
            ma5_ratio = (data['ma5'] / data['close']).values
            features.append(ma5_ratio)

        if 'ma20' in data.columns and 'close' in data.columns:
            ma20_ratio = (data['ma20'] / data['close']).values
            features.append(ma20_ratio)

        # 成交量特征
        if 'volume' in data.columns:
            volume_ma5 = data['volume'].rolling(5).mean().values
            volume_ratio = (data['volume'] / (volume_ma5 + 1e-8)).values
            features.append(volume_ratio)

        # 价格动量特征
        if 'close' in data.columns:
            price_change_5d = data['close'].pct_change(5).values
            price_change_10d = data['close'].pct_change(10).values
            features.extend([price_change_5d, price_change_10d])

        # 波动率特征
        if 'close' in data.columns:
            volatility_5d = data['close'].rolling(5).std().values
            volatility_20d = data['close'].rolling(20).std().values
            features.extend([volatility_5d, volatility_20d])

        return np.column_stack(features)

    def train(self, data: pd.DataFrame) -> Dict:
        """训练模型"""
        if not HAS_XGBOOST:
            return {"status": "error", "message": "XGBoost not available"}

        # 准备特征
        X = self.prepare_features(data)

        # 创建目标变量 (未来5日收益)
        future_return = data['close'].shift(-5) / data['close'] - 1
        y = future_return.values[:-5]  # 去掉最后5行

        # 去掉包含NaN的行
        valid_indices = ~np.isnan(y)
        X = X[valid_indices]
        y = y[valid_indices]

        # 数据标准化
        X_scaled = self.scaler.fit_transform(X)

        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        # 训练模型
        self.model.fit(X_train, y_train)

        # 评估模型
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)

        self.is_trained = True

        return {
            "status": "success",
            "mse": mse,
            "rmse": np.sqrt(mse),
            "feature_importance": self.model.feature_importances_.tolist()
        }

    def predict(self, data: pd.DataFrame) -> Dict:
        """预测"""
        if not HAS_XGBOOST:
            raise Exception("XGBoost不可用，请安装: pip install xgboost")

        if not self.is_trained:
            raise Exception("XGBoost模型尚未训练，请先调用train方法")

        try:
            X = self.prepare_features(data)
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)

            # 将预测转换为分数 (0-100)
            scores = []
            for pred in predictions[-10:]:  # 取最后10个预测
                score = 50 + pred * 500  # 转换为分数
                score = max(0, min(100, score))
                scores.append(score)

            return {
                "status": "success",
                "score": np.mean(scores),
                "trend": "up" if np.mean(scores) > 50 else "down",
                "confidence": 0.75,
                "predictions": predictions.tolist()
            }
        except Exception as e:
            raise Exception(f"XGBoost预测失败: {str(e)}")



class RandomForestRiskAnalyzer:
    """随机森林风险分析模型"""

    def __init__(self):
        """初始化随机森林模型"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False

    def prepare_risk_features(self, data: pd.DataFrame) -> np.ndarray:
        """准备风险特征"""
        features = []

        # 价格波动特征
        if 'close' in data.columns:
            returns = data['close'].pct_change().dropna()
            volatility = returns.rolling(20).std().values
            max_drawdown = (data['close'] / data['close'].expanding().max() - 1).values
            features.extend([volatility, max_drawdown])

        # 成交量波动
        if 'volume' in data.columns:
            vol_returns = data['volume'].pct_change().dropna()
            vol_volatility = vol_returns.rolling(20).std().values
            features.append(vol_volatility)

        # 技术指标风险
        if 'rsi' in data.columns:
            rsi = data['rsi'].values
            rsi_risk = np.abs(rsi - 50) / 50  # 偏离50的程度
            features.append(rsi_risk)

        return np.column_stack(features)

    def train(self, data: pd.DataFrame) -> Dict:
        """训练模型"""
        # 准备特征
        X = self.prepare_risk_features(data)

        # 创建风险标签 (0: 低风险, 1: 高风险)
        if 'volatility' in data.columns:
            volatility = data['volatility']
        else:
            volatility = data['close'].pct_change().rolling(20).std()

        # 基于波动率创建标签
        volatility_threshold = volatility.quantile(0.7)
        y = (volatility > volatility_threshold).astype(int).values[:-20]  # 去掉NaN

        # 去掉包含NaN的行
        valid_indices = ~np.isnan(y)
        X = X[valid_indices]
        y = y[valid_indices]

        if len(X) == 0:
            return {"status": "error", "message": "No valid data for training"}

        # 数据标准化
        X_scaled = self.scaler.fit_transform(X)

        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        # 训练模型
        self.model.fit(X_train, y_train)

        # 评估模型
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        self.is_trained = True

        return {
            "status": "success",
            "accuracy": accuracy,
            "feature_importance": self.model.feature_importances_.tolist()
        }

    def analyze_risk(self, data: pd.DataFrame) -> Dict:
        """分析风险"""
        if not self.is_trained:
            raise Exception("随机森林模型尚未训练，请先调用train方法")

        try:
            X = self.prepare_risk_features(data)
            X_scaled = self.scaler.transform(X[-1:].reshape(1, -1))

            # 预测风险概率
            risk_proba = self.model.predict_proba(X_scaled)[0]
            high_risk_prob = risk_proba[1]

            # 转换为评分
            score = 100 - high_risk_prob * 60  # 高风险概率转换为低分

            return {
                "status": "success",
                "score": score,
                "risk_level": "high" if score < 40 else "medium" if score < 60 else "low",
                "confidence": 0.70,
                "risk_probability": high_risk_prob
            }
        except Exception as e:
            raise Exception(f"随机森林风险分析失败: {str(e)}")


class GRUPredictor:
    """GRU价格序列预测模型"""

    def __init__(self, sequence_length: int = 30):
        """
        初始化GRU模型

        Args:
            sequence_length: 序列长度
        """
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = MinMaxScaler()
        self.is_trained = False

        if not HAS_KERAS:
            print("TensorFlow not available")

    def prepare_sequences(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备序列数据"""
        # 选择特征列
        feature_cols = ['close', 'volume', 'high', 'low']
        available_cols = [col for col in feature_cols if col in data.columns]

        if len(available_cols) == 0:
            raise ValueError("No valid feature columns found")

        # 标准化数据
        scaled_data = self.scaler.fit_transform(data[available_cols])

        # 创建序列
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            # 预测下一个收盘价
            y.append(scaled_data[i, 0])  # close价格

        return np.array(X), np.array(y)

    def build_model(self, input_shape: Tuple[int, int]) -> Sequential:
        """构建GRU模型"""
        if not HAS_KERAS:
            raise ImportError("TensorFlow not available")

        model = Sequential([
            GRU(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            GRU(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )

        return model

    def train(self, data: pd.DataFrame) -> Dict:
        """训练模型"""
        if not HAS_KERAS:
            return {"status": "error", "message": "TensorFlow not available"}

        try:
            # 准备序列数据
            X, y = self.prepare_sequences(data)

            if len(X) < 100:  # 数据太少
                return {"status": "error", "message": "Insufficient data for training"}

            # 划分训练测试集
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # 构建模型
            self.model = self.build_model((X.shape[1], X.shape[2]))

            # 训练模型
            history = self.model.fit(
                X_train, y_train,
                batch_size=32,
                epochs=20,
                validation_data=(X_test, y_test),
                verbose=0
            )

            # 评估模型
            test_loss, test_mae = self.model.evaluate(X_test, y_test, verbose=0)

            self.is_trained = True

            return {
                "status": "success",
                "test_loss": test_loss,
                "test_mae": test_mae,
                "epochs": len(history.history['loss'])
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def predict(self, data: pd.DataFrame) -> Dict:
        """预测"""
        if not HAS_KERAS:
            raise Exception("TensorFlow不可用，请安装: pip install tensorflow")

        if not self.is_trained:
            raise Exception("GRU模型尚未训练，请先调用train方法")

        try:
            # 准备最后的序列
            feature_cols = ['close', 'volume', 'high', 'low']
            available_cols = [col for col in feature_cols if col in data.columns]

            scaled_data = self.scaler.transform(data[available_cols])
            sequence = scaled_data[-self.sequence_length:].reshape(1, self.sequence_length, -1)

            # 预测
            prediction = self.model.predict(sequence, verbose=0)[0, 0]

            # 反标准化
            current_price = data['close'].iloc[-1]
            predicted_return = prediction * 0.02  # 假设标准化因子

            # 转换为评分
            if predicted_return > 0.02:
                score = 80 + min(predicted_return * 1000, 20)
            elif predicted_return > 0:
                score = 50 + predicted_return * 1500
            elif predicted_return > -0.02:
                score = 50 + predicted_return * 1500
            else:
                score = max(0, 30 + predicted_return * 1000)

            return {
                "status": "success",
                "score": max(0, min(100, score)),
                "prediction": "涨" if predicted_return > 0 else "跌",
                "confidence": 0.80,
                "predicted_return": predicted_return
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}



class ModelEnsemble:
    """模型集成器"""

    def __init__(self):
        """初始化集成模型"""
        self.xgb_model = XGBoostTrendPredictor()
        self.rf_model = RandomForestRiskAnalyzer()
        self.gru_model = GRUPredictor()

    def train_all(self, data: pd.DataFrame) -> Dict:
        """训练所有模型"""
        results = {}

        # 训练XGBoost
        try:
            results['xgboost'] = self.xgb_model.train(data)
        except Exception as e:
            results['xgboost'] = {"status": "error", "message": str(e)}

        # 训练随机森林
        try:
            results['random_forest'] = self.rf_model.train(data)
        except Exception as e:
            results['random_forest'] = {"status": "error", "message": str(e)}

        # 训练GRU
        try:
            results['gru'] = self.gru_model.train(data)
        except Exception as e:
            results['gru'] = {"status": "error", "message": str(e)}

        return results

    def predict_all(self, data: pd.DataFrame) -> Dict:
        """预测所有模型"""
        results = {}

        # XGBoost预测
        try:
            results['xgboost'] = self.xgb_model.predict(data)
        except Exception as e:
            results['xgboost'] = {"status": "error", "message": str(e)}

        # 随机森林预测
        try:
            results['random_forest'] = self.rf_model.analyze_risk(data)
        except Exception as e:
            results['random_forest'] = {"status": "error", "message": str(e)}

        # GRU预测
        try:
            results['gru'] = self.gru_model.predict(data)
        except Exception as e:
            results['gru'] = {"status": "error", "message": str(e)}

        # 集成评分
        final_score = self._ensemble_score(results)

        return {
            "final_score": final_score,
            "individual_results": results,
            "model_count": len([r for r in results.values() if r.get('status') == 'success'])
        }

    def _ensemble_score(self, results: Dict) -> float:
        """集成评分"""
        scores = []
        weights = []

        for model_name, result in results.items():
            if result.get('status') == 'success':
                if 'score' in result:
                    scores.append(result['score'])
                    # 根据模型类型设置权重
                    if model_name == 'xgboost':
                        weights.append(0.4)
                    elif model_name == 'gru':
                        weights.append(0.3)
                    elif model_name == 'random_forest':
                        weights.append(0.3)

        if len(scores) == 0:
            return 50.0  # 默认分数

        # 加权平均
        weighted_score = sum(s * w for s, w in zip(scores, weights))
        return weighted_score


# 便捷函数
def create_ml_ensemble() -> ModelEnsemble:
    """创建ML模型集成器"""
    return ModelEnsemble()

def quick_predict(data: pd.DataFrame) -> Dict:
    """快速预测"""
    ensemble = create_ml_ensemble()
    return ensemble.predict_all(data)
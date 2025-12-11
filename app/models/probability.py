from typing import Dict, Any, Optional
import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from app.config import MODEL_ARTIFACTS_PATH, SETTINGS

model_cache = {}

def load_model(model_name: str = "default"):
    global model_cache
    
    if model_name in model_cache:
        return model_cache[model_name]
    
    model_path = os.path.join(MODEL_ARTIFACTS_PATH, f"{model_name}_model.pkl")
    
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            model_cache[model_name] = model
            return model
        except Exception as e:
            print(f"Error loading model {model_name}: {e}")
    
    return None

def calculate_implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 0:
        return 0.0
    return round(1 / decimal_odds, 4)

def calculate_fair_odds(probability: float) -> float:
    if probability <= 0:
        return float('inf')
    return round(1 / probability, 2)

def extract_features(selection_name: str, sport: str, context: Optional[Dict] = None) -> np.ndarray:
    context = context or {}
    
    features = []
    
    win_rate = context.get("win_rate", 0.5)
    recent_form = context.get("recent_form", 0.5)
    is_favorite = context.get("is_favorite", False)
    is_home = context.get("is_home", False)
    ranking_diff = context.get("ranking_diff", 0)
    implied_prob = context.get("implied_prob", 0.5)
    
    features.append(win_rate)
    features.append(recent_form)
    features.append(1.0 if is_favorite else 0.0)
    features.append(1.0 if is_home else 0.0)
    features.append(ranking_diff / 100.0)
    features.append(implied_prob)
    
    return np.array(features).reshape(1, -1)

def get_model_prediction(selection_name: str, sport: str, context: Optional[Dict] = None) -> float:
    model = load_model("default")
    
    if model is not None and context:
        try:
            features = extract_features(selection_name, sport, context)
            prob = model.predict_proba(features)[0][1]
            return float(round(prob, 4))
        except Exception as e:
            print(f"Model prediction error: {e}")
    
    return get_heuristic_probability(selection_name, sport, context)

def get_heuristic_probability(selection_name: str, sport: str, context: Optional[Dict] = None) -> float:
    context = context or {}
    
    implied_prob = context.get("implied_prob", 0.5)
    is_favorite = context.get("is_favorite", implied_prob > 0.5)
    win_rate = context.get("win_rate", 0.55 if is_favorite else 0.45)
    recent_form = context.get("recent_form", 0.55 if is_favorite else 0.45)
    is_home = context.get("is_home", False)
    
    base_prob = implied_prob
    
    if implied_prob >= 0.85:
        if win_rate >= 0.65:
            adjustment = 0.05
        elif win_rate >= 0.55:
            adjustment = 0.03
        else:
            adjustment = 0.01
    elif implied_prob >= 0.75:
        if win_rate >= 0.60:
            adjustment = 0.04
        else:
            adjustment = 0.02
    elif implied_prob >= 0.60:
        adjustment = 0.03
    else:
        adjustment = 0.02
    
    if is_home:
        adjustment += 0.02
    if recent_form > 0.6:
        adjustment += 0.02
    
    base_prob = implied_prob + adjustment
    
    return min(0.98, max(0.02, round(base_prob, 4)))

def calculate_edge(model_prob: float, implied_prob: float) -> float:
    return round(model_prob - implied_prob, 4)

def train_model(training_data: list, model_name: str = "default") -> bool:
    if not training_data or len(training_data) < 10:
        print("Insufficient training data")
        return False
    
    try:
        X = []
        y = []
        
        for record in training_data:
            features = [
                record.get("win_rate", 0.5),
                record.get("recent_form", 0.5),
                1.0 if record.get("is_favorite", False) else 0.0,
                1.0 if record.get("is_home", False) else 0.0,
                record.get("ranking_diff", 0) / 100.0,
                record.get("implied_prob", 0.5),
            ]
            X.append(features)
            y.append(1 if record.get("won", False) else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42
        )
        model.fit(X, y)
        
        os.makedirs(MODEL_ARTIFACTS_PATH, exist_ok=True)
        model_path = os.path.join(MODEL_ARTIFACTS_PATH, f"{model_name}_model.pkl")
        joblib.dump(model, model_path)
        
        global model_cache
        model_cache[model_name] = model
        
        print(f"Model trained and saved: {model_path}")
        return True
        
    except Exception as e:
        print(f"Error training model: {e}")
        return False

def generate_synthetic_training_data(n_samples: int = 500) -> list:
    np.random.seed(42)
    training_data = []
    
    for _ in range(n_samples):
        win_rate = np.random.uniform(0.3, 0.8)
        recent_form = np.random.uniform(0.3, 0.8)
        is_favorite = np.random.random() > 0.5
        is_home = np.random.random() > 0.5
        ranking_diff = np.random.randint(-50, 50)
        implied_prob = np.random.uniform(0.3, 0.9)
        
        win_prob = (
            0.3 * win_rate +
            0.2 * recent_form +
            0.15 * (1 if is_favorite else 0) +
            0.1 * (1 if is_home else 0) +
            0.15 * (1 - ranking_diff / 100) +
            0.1 * implied_prob
        )
        win_prob = min(0.95, max(0.05, win_prob))
        
        won = np.random.random() < win_prob
        
        training_data.append({
            "win_rate": win_rate,
            "recent_form": recent_form,
            "is_favorite": is_favorite,
            "is_home": is_home,
            "ranking_diff": ranking_diff,
            "implied_prob": implied_prob,
            "won": won,
        })
    
    return training_data

def initialize_model():
    model = load_model("default")
    if model is None:
        print("No trained model found. Training with synthetic data...")
        training_data = generate_synthetic_training_data(500)
        train_model(training_data, "default")

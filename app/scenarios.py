"""
Sistema de Modos y Escenarios para CRI Metrics.
Permite alternar entre datos REALES y SIMULADOS,
y definir múltiples escenarios de mercado predefinidos.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Estado global del modo (en memoria, por sesión)
class ModeState:
    """Estado del modo de operación del sistema."""
    
    MODE_REAL = "REAL"
    MODE_SIMULATION = "SIMULATION"
    
    def __init__(self):
        self.mode = self.MODE_REAL  # Por defecto: REAL
        self.active_scenario = None  # Solo relevante en SIMULATION
        self.last_changed = datetime.now(timezone.utc)
    
    def set_mode(self, mode: str):
        if mode not in (self.MODE_REAL, self.MODE_SIMULATION):
            raise ValueError(f"Modo inválido: {mode}. Use REAL o SIMULATION")
        self.mode = mode
        self.last_changed = datetime.now(timezone.utc)
        if mode == self.MODE_REAL:
            self.active_scenario = None
    
    def set_scenario(self, scenario_id: str):
        if scenario_id not in SCENARIOS:
            raise ValueError(f"Escenario inválido: {scenario_id}")
        self.mode = self.MODE_SIMULATION
        self.active_scenario = scenario_id
        self.last_changed = datetime.now(timezone.utc)
    
    def get_status(self) -> Dict:
        return {
            "mode": self.mode,
            "active_scenario": self.active_scenario,
            "scenario_name": SCENARIOS.get(self.active_scenario, {}).get("name") if self.active_scenario else None,
            "last_changed": self.last_changed.isoformat(),
            "is_simulation": self.mode == self.MODE_SIMULATION,
        }

# Singleton global
_system_mode = ModeState()

def get_mode_state() -> ModeState:
    return _system_mode

# ============================================================
# ESCENARIOS PREDEFINIDOS
# ============================================================

SCENARIOS = {
    "normal": {
        "id": "normal",
        "name": "Mercado Normal",
        "description": "Condiciones estables de mercado. Datos reales del momento.",
        "icon": "📊",
        "color": "#58a6ff",
        "params": {
            "GSPI": 50.0,   # Precios GPU normales
            "SHPD": 50.0,   # Demanda hardware estable
            "LTCR": 50.0,   # Contratos a largo plazo estables
            "CFBR": 50.0,   # Capitalización crypto/media
            "UOR": 50.0,    # Ocupación normal
        }
    },
    
    "gpu_shortage": {
        "id": "gpu_shortage",
        "name": "Escasez GPU",
        "description": "Demanda masiva de GPUs (IA/ML boom). Precios spot altos, baja infrautilización.",
        "icon": "🔥",
        "color": "#f85149",
        "params": {
            "GSPI": 85.0,   # Precios spot muy altos
            "SHPD": 20.0,   # Poca deflación (demanda alta)
            "LTCR": 30.0,   # Contratos seguros por demanda
            "CFBR": 40.0,   # Capital fluye hacia infra
            "UOR": 15.0,    # Ocupación casi total
        }
    },
    
    "crypto_crash": {
        "id": "crypto_crash",
        "name": "Crash Crypto",
        "description": "Colapso del mercado crypto. Mineros venden GPUs, capital huye.",
        "icon": "💥",
        "color": "#f85149",
        "params": {
            "GSPI": 70.0,   # Precios caen pero hay dumping
            "SHPD": 85.0,   # Deflación masiva (mineros venden)
            "LTCR": 75.0,   # Desconfianza en contratos
            "CFBR": 90.0,   # Capital quemado/escapando
            "UOR": 80.0,    # Infrautilización masiva
        }
    },
    
    "bear_market": {
        "id": "bear_market",
        "name": "Bear Market",
        "description": "Mercado bajista general. Todo el ecosistema IA en contracción.",
        "icon": "🐻",
        "color": "#d29922",
        "params": {
            "GSPI": 60.0,
            "SHPD": 70.0,
            "LTCR": 70.0,
            "CFBR": 75.0,
            "UOR": 70.0,
        }
    },
    
    "bull_run": {
        "id": "bull_run",
        "name": "Bull Run",
        "description": "Mercado alcista. Inversión masiva en IA, todo verde.",
        "icon": "🚀",
        "color": "#3fb950",
        "params": {
            "GSPI": 30.0,   # Escala económica baja precios
            "SHPD": 20.0,   # Demanda sostiene precios
            "LTCR": 15.0,   # Contratos largos seguros
            "CFBR": 15.0,   # Mucho capital disponible
            "UOR": 10.0,    # Todo ocupado
        }
    },
    
    "supply_crisis": {
        "id": "supply_crisis",
        "name": "Crisis de Suministro",
        "description": "Problemas en la cadena de suministro (TSMC, Samsung). GPUs escasas.",
        "icon": "⚠️",
        "color": "#f85149",
        "params": {
            "GSPI": 95.0,   # Precios spot extremos
            "SHPD": 90.0,   # Deflación por crisis (nadie puede comprar)
            "LTCR": 60.0,   # Contratos inciertos por falta de hardware
            "CFBR": 50.0,   # Capital atrapado
            "UOR": 20.0,    # Lo que hay, está ocupado
        }
    },
    
    "regulatory_shock": {
        "id": "regulatory_shock",
        "name": "Shock Regulatorio",
        "description": "Nuevas regulaciones (UE AI Act, export controls). Incertidumbre legal.",
        "icon": "📜",
        "color": "#d29922",
        "params": {
            "GSPI": 45.0,
            "SHPD": 40.0,
            "LTCR": 95.0,   # Riesgo regulatorio extremo
            "CFBR": 60.0,   # Capital se retira por incertidumbre
            "UOR": 55.0,    # Congelamiento de proyectos
        }
    },
    
    "infrastructure_boom": {
        "id": "infrastructure_boom",
        "name": "Boom Infraestructura",
        "description": "Mega-inversión en data centers ( hyperscalers ). Todo construyendo.",
        "icon": "🏗️",
        "color": "#3fb950",
        "params": {
            "GSPI": 40.0,
            "SHPD": 25.0,   # Mucha compra de hardware
            "LTCR": 20.0,   # Contratos largos firmados
            "CFBR": 35.0,   # Capital fluye a infra
            "UOR": 5.0,     # Todo ocupado y construyendo más
        }
    },
    
    "ai_winter": {
        "id": "ai_winter",
        "name": "Invierno IA",
        "description": "Desilusión con IA. Proyectos cancelados, GPUs sobran.",
        "icon": "❄️",
        "color": "#a371f7",
        "params": {
            "GSPI": 25.0,   # Precios caen por sobreoferta
            "SHPD": 85.0,   # Deflación masiva
            "LTCR": 80.0,   # Contratos rotos
            "CFBR": 70.0,   # Capital se retira
            "UOR": 85.0,    # Infraestructura vacía
        }
    },
    
    "energy_crisis": {
        "id": "energy_crisis",
        "name": "Crisis Energética",
        "description": "Precios energía altos. Data centers caros, mineros apagan.",
        "icon": "⚡",
        "color": "#d29922",
        "params": {
            "GSPI": 55.0,
            "SHPD": 75.0,   # Mineros venden GPUs
            "LTCR": 65.0,   # Costos energía afectan contratos
            "CFBR": 45.0,
            "UOR": 60.0,    # Apagado selectivo
        }
    },
}

def get_scenario_list() -> List[Dict]:
    """Retorna lista de escenarios para el frontend."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "icon": s["icon"],
            "color": s["color"],
            "params": s["params"],
            "cri_preview": _preview_cri(s["params"]),
        }
        for s in SCENARIOS.values()
    ]

def _preview_cri(params: Dict[str, float]) -> float:
    """Calcula CRI preview para un escenario."""
    weights = {
        "GSPI": 0.25,
        "SHPD": 0.15,
        "LTCR": 0.20,
        "CFBR": 0.20,
        "UOR": 0.20,
    }
    cri = sum(params[k] * weights[k] for k in weights)
    return round(cri, 2)

def get_zone(cri: float) -> str:
    if cri <= 30:
        return "LOW"
    elif cri <= 65:
        return "MODERATE"
    else:
        return "CRITICAL"

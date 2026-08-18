"""
Persona DNA Framework
=====================
A modular framework for building AI personalities with memory, growth, and proactive care.

Core pillars:
- Soul Engine: YAML-based personality configuration and system prompt generation
- Memory Map: Layered memory storage with concept association graph
- Proactive Care: Rule/time-based proactive engagement system
- Growth Engine: Three-layer cell model with forgetting and anti-erosion protection
"""

__version__ = "0.1.0"
__author__ = "Persona DNA Contributors"

from persona_dna.soul import SoulEngine
from persona_dna.memory import MemorySystem
from persona_dna.map import ConceptMap
from persona_dna.care import ProactiveCare
from persona_dna.growth import GrowthEngine
from persona_dna.config import Config

__all__ = [
    "SoulEngine",
    "MemorySystem",
    "ConceptMap",
    "ProactiveCare",
    "GrowthEngine",
    "Config",
]

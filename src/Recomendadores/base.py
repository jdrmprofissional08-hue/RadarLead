
from abc import ABC, abstractmethod


class Recomendador(ABC):

    @abstractmethod
    def recomendar(self, empresas: list, perfil: dict) -> list:
        pass

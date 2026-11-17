"""Exceções do RadarLead.

Módulo definido em conjunto pelo grupo. Todas herdam de RadarLeadError,
então quem chama pode capturar só a base quando não precisar distinguir.
"""


class RadarLeadError(Exception):
    """Base de todas as exceções do projeto."""


# --- Dados inválidos -------------------------------------------------------

class DadosInvalidosError(RadarLeadError):
    """Um dado de entrada não respeita as regras do domínio."""


class PerfilInvalidoError(DadosInvalidosError):
    """Perfil de cliente com campos inválidos."""


class EmpresaInvalidaError(DadosInvalidosError):
    """Empresa com campos inválidos."""


# --- Registros inexistentes ------------------------------------------------

class RegistroNaoEncontradoError(RadarLeadError):
    """Consulta por um registro que não existe."""


class PerfilNaoEncontradoError(RegistroNaoEncontradoError):
    """Perfil não existe no repositório."""


class EmpresaNaoEncontradaError(RegistroNaoEncontradoError):
    """Empresa não existe no repositório."""


class ProspeccaoNaoEncontradaError(RegistroNaoEncontradoError):
    """Prospecção não existe no repositório."""


# --- Falhas de componentes -------------------------------------------------

class RecomendadorError(RadarLeadError):
    """O recomendador falhou ou devolveu uma resposta fora do contrato."""


class PersistenciaError(RadarLeadError):
    """Falha ao ler ou gravar dados (arquivo JSON, banco de dados...)."""

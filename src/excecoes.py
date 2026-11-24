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


class EmpresaUsuariaInvalidaError(DadosInvalidosError):
    """Empresa usuária (quem usa o RadarLead) com campos inválidos."""


class ProdutoInvalidoError(DadosInvalidosError):
    """Produto ou serviço com campos inválidos."""


# --- Registros inexistentes ------------------------------------------------

class RegistroNaoEncontradoError(RadarLeadError):
    """Consulta por um registro que não existe."""


class PerfilNaoEncontradoError(RegistroNaoEncontradoError):
    """Perfil não existe no repositório."""


class EmpresaNaoEncontradaError(RegistroNaoEncontradoError):
    """Empresa não existe no repositório."""


class ProspeccaoNaoEncontradaError(RegistroNaoEncontradoError):
    """Prospecção não existe no repositório."""


class EmpresaUsuariaNaoEncontradaError(RegistroNaoEncontradoError):
    """Empresa usuária ainda não cadastrada (ou inexistente)."""


class ProdutoNaoEncontradoError(RegistroNaoEncontradoError):
    """Produto não existe (ou pertence a outra empresa usuária)."""


# --- Conflitos -------------------------------------------------------------

class DuplicadoError(RadarLeadError):
    """O registro conflita com outro já existente (CNPJ, e-mail ou nome repetido)."""


# --- Falhas de componentes -------------------------------------------------

class RecomendadorError(RadarLeadError):
    """O recomendador falhou ou devolveu uma resposta fora do contrato."""


class PersistenciaError(RadarLeadError):
    """Falha ao ler ou gravar dados (arquivo JSON, banco de dados...)."""


class ReferenciaInexistenteError(PersistenciaError):
    """Código válido, mas ausente das tabelas de referência do banco.

    Não é indisponibilidade: o banco respondeu. Falta carregar o catálogo
    (municípios, CNAEs...). Estende PersistenciaError para que o código que já
    captura PersistenciaError continue funcionando.
    """

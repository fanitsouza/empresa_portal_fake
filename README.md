# Portal Fake Soluções Digitais - Hyperautomation

Este projeto faz parte da disciplina **Técnicas de Hyperautomation** e tem como objetivo automatizar o fluxo completo de atendimento, recepção de documentos, validação, extração de dados, cadastro no sistema e suporte via SAC da Empresa Portal Fake Soluções Digitais.

---

## 👥 Equipe

| Integrante | Responsabilidade |
|---|---|
| **Fani Batista** | Líder da equipe, modelagem BPMN, regras de negócio, relatório técnico e validação geral |
| **Lua Maquiné** | Desenvolvimento da rotina de recebimento, leitura de solicitações e resposta automática ao cliente |
| **Gustavo Martins** | Organização de arquivos, validação de documentos, GitHub e GitFlow |

---

## 🏛️ Arquitetura Completa do Pipeline (5 Processos)

```text
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                PIPELINE HYPERAUTOMATION                                  │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
   [Processo 1]  ➔ Atendimento: Envio de Ficha (DOCX) + Validação Documental (3 Obrigatórios)
         ↓ (Documentos Validados e salvos em Documentos_OK)
   [Processo 2]  ➔ Organização de Dados: Extração dos PDFs + Alimentação da Planilha Mestra (.xlsx) + Arquivamento
         ↓ (Planilha Mestra Atualizada)
   [Processo 3]  ➔ Setor de Cadastro: Consulta CPF no Portal Fake + Cadastro RPA + Pastas Erro/Concluído
         ↓ (Status do Cadastro Atualizado)
   [Processo 4]  ➔ Setor de SAC: Consulta Status + E-mails de Confirmação/Erro + Planilha Status_SAC
         ↓ (Dados consolidados para auditoria e gestão)
   [Processo 5]  ➔ Relatórios e Métricas de Performance (relatorio_sac.json / Dashboards)
```

---

## 📦 Detalhamento dos Processos

### 1. Processo 1: Atendimento ao Cliente (`processo_1_envio_fichas.py` e `processo_2_validacao_docs.py`)
- Dispara a Ficha de Cadastro preenchida em Word (`.docx`) por e-mail para o cliente assinar.
- Monitora a caixa de entrada (Gmail via IMAP) para receber os documentos anexos.
- Valida a presença dos **3 documentos obrigatórios**:
  - *Ficha Cadastral Assinada*
  - *Documento Oficial com Foto (RG / CNH)*
  - *Comprovante de Residência*
- Se incompleto: move para `ERP_Portal_Fake/Documentos_Pendentes` e notifica o cliente por e-mail sobre o que faltou.
- Se completo: move para `ERP_Portal_Fake/Documentos_OK` e `Documentos_Aprovados/`, disparando confirmação com protocolo `#2026-XXXX`.

### 2. Processo 2: Organização de Dados (`processo_3_extracao_planilha.py`)
- Recebe a documentação de `Documentos_OK` / `Documentos_Aprovados`.
- Abre os PDFs e extrai os campos estruturados (*Nome, CPF, E-mail, Telefone, Nascimento e Endereço*).
- Alimenta e valida a `resources/planilha_mestra.xlsx` com formatação executiva, sem duplicidade por CPF.
- Arquiva os documentos processados na pasta `resources/ERP_Portal_Fake/Arquivados`.
- Encaminha a planilha mestra atualizada para o setor de cadastro.

### 3. Processo 3: Setor de Cadastro (`processo_4_cadastro_portal.py` / `processo_cadastro.py`)
- Recebe a `planilha_mestra.xlsx` e acessa o Portal Fake.
- **Consulta CPF no Portal Fake**:
  - Se o cliente **já estiver cadastrado**: registra como `DUPLICADO`, salva evidência/screenshot na pasta `resources/ERP_Portal_Fake/Cadastro_com_erro` e atualiza a planilha mestra.
  - Se o cliente **não estiver cadastrado**:
    - Preenche o formulário e salva o cadastro via Playwright RPA.
    - Valida o salvamento:
      * Se falhou (erro de formulário): registra `ERRO_CADASTRO`, salva na pasta `resources/ERP_Portal_Fake/Cadastro_com_erro`.
      * Se teve sucesso: registra `SUCESSO`, salva na pasta `resources/ERP_Portal_Fake/Cadastro_Concluido`.
- Atualiza as colunas de auditoria na `planilha_mestra.xlsx` (`Status Cadastro`, `Motivo Erro Cadastro`, `Data Cadastro`).
- Encaminha os resultados para o SAC.

### 4. Processo 4: Setor de SAC (`processo_sac.py` / `processo_4_sac.py`)
- Recebe o status de cadastro da planilha mestra.
- Analisa o status de cada cliente:
  - **Se Sucesso (`SUCESSO` / `ATIVO`)**:
    - Dispara e-mail corporativo em HTML de **Confirmação e Boas-Vindas** com dados cadastrais e protocolo SAC `#SAC-2026-XXXX`.
    - Registra status `CONFIRMACAO_ENVIADA`.
  - **Se Erro ou Duplicado (`DUPLICADO` / `ERRO_CADASTRO`)**:
    - Dispara e-mail corporativo em HTML informando o **motivo específico da inconsistência** e instruções de regularização.
    - Registra status `NOTIFICACAO_ERRO_ENVIADA`.
- Cria e formata a planilha corporativa `resources/Status_SAC.xlsx` (e cópia no ERP).
- Atualiza as colunas `Status SAC`, `Protocolo SAC` e `Data Envio SAC` na `planilha_mestra.xlsx`.
- Consolida e exporta os dados para o Processo 5 de Relatórios (`resources/relatorio_sac.json`).

### 5. Processo 5: Relatórios e Métricas (`resources/relatorio_sac.json`)
- Recebe os dados consolidados do SAC contendo indicadores de desempenho:
  - Total de solicitações atendidas
  - Taxa de sucesso de cadastros (%)
  - Total de duplicidades e falhas tratadas
  - Log detalhado de auditoria por protocolo e CPF

---

## 🚀 Como Executar

### 1. Painel Interativo
Basta rodar o comando abaixo para abrir o menu interativo com todas as opções:
```bash
python main.py
```

---

### 2. Execuções Isoladas

```bash
# Processo 1: Envio de Fichas para Assinatura
python main.py --processo 1

# Processo 2: Baixar e Validar Documentos Recebidos
python main.py --processo 2 --modo real

# Processo 3: Extrair Dados de PDFs e Salvar na Planilha Mestra
python main.py --processo 3

# Processo 4: Setor de Cadastro no Portal Fake (Consulta CPF + Validação + Pastas)
python main.py --processo 4 --no-headless

# Processo 5: Setor de SAC (E-mails Confirmação/Erro + Planilha Status_SAC + Relatórios)
python main.py --processo 5
```

---

### 3. Pipelines Integradas / Encadeadas

```bash
# Pipeline Validação + Extração (Processos 2 + 3)
python main.py --pipeline validacao-extracao --modo real

# Pipeline Cadastro + SAC (Processos 4 + 5)
python main.py --pipeline cadastro-sac --no-headless

# Pipeline Atendimento Completo (Processos 2 + 3 + 4 + 5)
python main.py --pipeline atendimento-completo --modo real --no-headless

# Pipeline Total de Ponta a Ponta (Processos 1 + 2 + 3 + 4 + 5)
python main.py --pipeline completo --modo real --no-headless
```

---

## ⚙️ Configurações (.env)

Crie o arquivo `HyperAutomation/source/.env` baseado em `.env.example`:

```env
EMAIL_REMETENTE=seu_email@gmail.com
EMAIL_SENHA_APP=sua_senha_de_app_16_digitos
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
```

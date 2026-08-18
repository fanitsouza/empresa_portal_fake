# Portal Fake Soluções Digitais - Hyperautomation

Este projeto faz parte da disciplina **Técnicas de Hyperautomation** e tem como objetivo automatizar o fluxo completo de atendimento, recepção de documentos, validação, extração de dados e cadastro no sistema da Empresa Portal Fake Soluções Digitais.

---

## 👥 Equipe

| Integrante | Responsabilidade |
|---|---|
| **Fani Batista** | Líder da equipe, modelagem BPMN, regras de negócio, relatório técnico e validação geral |
| **Lua Maquiné** | Desenvolvimento da rotina de recebimento, leitura de solicitações e resposta automática ao cliente |
| **Gustavo Martins** | Organização de arquivos, validação de documentos, GitHub e GitFlow |

---

## 🏛️ Arquitetura do Pipeline

```text
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │                               PIPELINE HYPERAUTOMATION                           │
 └──────────────────────────────────────────────────────────────────────────────────┘
   [Processo 1]  ➔ Envio de Fichas de Cadastro por E-mail para Assinatura (Ciclo Fechado)
         ↓ (Cliente assina e responde com os documentos)
   [Processo 2]  ➔ Leitura de E-mails (IMAP) + Validação Documental dos 3 Itens Obrigatórios
         ↓ (Documentos Aprovados)
   [Processo 3]  ➔ Extração dos Dados do PDF + Alimentação da Planilha Mestra (.xlsx)
         ↓ (Planilha Mestra Atualizada)
   [Processo 4]  ➔ Carga e Cadastro Automatizado no Portal Fake via Playwright / API
```

---

## 📦 Detalhamento dos 4 Processos

1. **Processo 1: Envio de Fichas para Assinatura** (`processo_1_envio_fichas.py`)
   - Extrai clientes do Portal Fake ou lista base.
   - Gera a Ficha de Cadastro preenchida em Word (`.docx`).
   - Dispara e-mail com a ficha em anexo solicitando a assinatura do cliente.

2. **Processo 2: Baixar e Validar Documentação** (`processo_2_validacao_docs.py`)
   - Monitora a caixa de entrada (Gmail via IMAP) ou pasta de downloads.
   - Valida a presença dos **3 documentos obrigatórios**:
     - *Ficha Cadastral Assinada*
     - *Documento Oficial com Foto (RG / CNH)*
     - *Comprovante de Residência*
   - Separa os arquivos em `Documentos_OK` e `Documentos_Pendentes`.
   - Envia e-mail de resposta automática ao cliente (confirmação com protocolo `#2026-XXXX` ou notificação de pendências).

3. **Processo 3: Extração de Dados e Planilha Mestra** (`processo_3_extracao_planilha.py`)
   - Extrai os campos dos PDFs aprovados: *Nome, CPF, E-mail, Telefone, Nascimento e Endereço*.
   - Gera o arquivo `resources/saida_extracao_pdf.json`.
   - Insere ou atualiza os registros na `resources/planilha_mestra.xlsx` com formatação e sem duplicidade por CPF.
   - Move os PDFs processados para a pasta de arquivamento (`resources/ERP_Portal_Fake/Arquivados`).

4. **Processo 4: Cadastro Automatizado no Portal Fake** (`processo_4_cadastro_portal.py`)
   - Lê os registros aprovados na `planilha_mestra.xlsx`.
   - Executa a inserção automatizada no Portal Fake via Playwright RPA (ou API/ML).
   - Salva evidências visuais em `resources/screenshots/` e logs de auditoria em `resources/logs/`.

---

## 🚀 Como Executar

### 1. Painel Interativo
Basta rodar o comando abaixo para abrir o menu interativo com todas as opções:
```bash
python3 main.py
```

---

### 2. Execuções Isoladas

```bash
# Executar apenas o Processo 1 (Envio de Fichas)
python3 main.py --processo 1

# Executar apenas o Processo 2 (Baixar e Validar Documentos)
python3 main.py --processo 2 --modo real

# Executar apenas o Processo 3 (Extrair PDF e Alimentar Planilha Mestra)
python3 main.py --processo 3

# Executar apenas o Processo 4 (Cadastrar no Portal Fake a partir da Planilha)
python3 main.py --processo 4 --no-headless
```

---

### 3. Pipelines Conectados / Encadeados

```bash
# Processo 2 + 3 (Baixar ➔ Validar ➔ Extrair para a Planilha Mestra)
python3 main.py --pipeline validacao-extracao --modo real

# Processo 2 + 3 + 4 (Atendimento Completo: Validar ➔ Planilha ➔ Portal Fake)
python3 main.py --pipeline atendimento-completo --modo real --no-headless

# Pipeline Total (Processos 1 + 2 + 3 + 4)
python3 main.py --pipeline completo --modo real --no-headless
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

# Projeto Icarus

**Bot de governança autônoma com integração Web3 + IA.**

Este projeto combina contratos inteligentes (Solidity/Ethereum) com um bot alimentado por IA (Gemini / DeepSeek) para participar automaticamente de uma DAO — analisando propostas, votando e executando decisões de governança on-chain.

## Arquitetura

```
moltbook-heartbeat.sh          # Heartbeat para rede social Moltbook
moltbook-personality.example.json  # Exemplo de personalidade do agente
web3-ai-dao/                   # Núcleo DAO on-chain + bot
├── contracts/
│   ├── GovernanceToken.sol    # ERC20 AIGOV (1M supply)
│   ├── AIStakeholderDAO.sol   # DAO com proposals, votação, quorum
│   └── ReputationNFT.sol      # ERC721 soulbound com níveis e XP
├── bot/
│   └── governance_bot.py      # Bot autônomo que analisa e vota
├── scripts/
│   ├── deploy_all.js          # Deploy completo + distribuição
│   ├── deploy_hardhat.js
│   ├── deploy_reputation.js
│   └── interact.py            # CLI interativa para criar/votar proposals
├── hardhat.config.js
├── package.json
└── .env.example
```

## Contratos

### GovernanceToken (`AIGOV`)
- ERC20 + ERC20Permit + Ownable
- Supply máximo: 1.000.000 tokens
- Mint restrito ao owner
- Burn permissionado

### AIStakeholderDAO
- Criação de propostas com descrição, valor e destinatário
- Votação ponderada por saldo de tokens + reputação
- Quorum mínimo de 10.000 tokens
- Período de votação: 3 dias
- Execução automática de propostas aprovadas
- Sistema de delegação de poder de voto

### ReputationNFT
- ERC721 soulbound (não transferível)
- Níveis: BRONZE → SILVER → GOLD → DIAMOND
- Multiplicador de voto: 1x → 2x → 3x → 5x
- XP ganho por votar (+10) e criar propostas (+25)

## Bot de Governança

O bot (`governance_bot.py`) opera em ciclo contínuo:

1. Conecta-se à rede Ethereum (Hardhat local ou remota)
2. Lê proposals pendentes do contrato DAO
3. Analisa cada proposta usando:
   - **Gemini 2.0 Flash** (primário)
   - **DeepSeek Chat** (fallback)
   - **Keyword matching** (fallback final)
4. Vota FOR ou AGAINST com base na análise
5. Executa proposals aprovadas automaticamente
6. Exibe status com saldo, reputação e poder de voto

### Configuração

```bash
cp .env.example .env
# Preencha as chaves de API e endereços dos contratos
```

| Variável | Descrição |
|---|---|
| `RPC_URL` | URL do nó Ethereum |
| `DEPLOYER_PRIVATE_KEY` | Chave da conta deployer |
| `BOT_PRIVATE_KEY` | Chave da conta do bot |
| `TOKEN_ADDRESS` | Endereço do GovernanceToken |
| `DAO_ADDRESS` | Endereço do AIStakeholderDAO |
| `REPUTATION_NFT_ADDRESS` | Endereço do ReputationNFT |
| `GEMINI_API_KEY` | API Key do Google Gemini |
| `DEEPSEEK_API_KEY` | API Key do DeepSeek |
| `BOT_CYCLE_INTERVAL` | Intervalo do ciclo em segundos |

## Deploy

```bash
# 1. Iniciar nó Hardhat local
npm run node

# 2. Compilar contratos
npm run compile

# 3. Fazer deploy
npm run deploy
```

## Execução

```bash
# Bot autônomo
npm run bot

# CLI interativa
npm run interact
```

## Moltbook Heartbeat

O script `moltbook-heartbeat.sh` é um agente autônomo para a rede social Moltbook:

- Verifica o feed e busca por posts relevantes
- Upvota posts alinhados com os interesses configurados
- Comenta com mensagens contextuais baseadas em keywords
- Resolve desafios de verificação (cálculos aritméticos)
- Mantém estado entre execuções

### Configuração do Moltbook

```bash
cp moltbook-personality.example.json ~/.config/moltbook/personality.json
# Edite o arquivo de personalidade conforme desejado
```

## Licença

MIT

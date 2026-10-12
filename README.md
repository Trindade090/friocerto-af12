# FrioCerto — Monitoramento de Temperatura de Câmaras Frias (IoT)

**AF12 — Atividade Formativa Integradora U1+U2**
Disciplina: Arquiteturas de Computação para IoT e Big Data (04803-80)
Turma: 493-02AN | Professor: Giovane de Morais
Aluno: João Victor Trindade Souza — RA 8169585

## Contexto

A FrioCerto monitora a temperatura das câmaras frias de 14 filiais (região do ABC), onde a faixa aceitável é de **2 °C a 8 °C**. Este repositório contém o laboratório funcional que simula os 14 sensores, ingere as leituras e exibe tudo em um dashboard com alerta.

## Arquitetura (fluxo de dados)

```
Sensor (produtor.py) → Mosquitto (MQTT) → Telegraf → InfluxDB → Grafana
```

| Componente | Função | Porta |
|---|---|---|
| Mosquitto | Broker MQTT (publicação/assinatura) | 1883 |
| Telegraf | Consome os tópicos MQTT e grava no InfluxDB | — |
| InfluxDB 2 | Banco de séries temporais (bucket `sensores`) | 8086 |
| Grafana | Dashboard e regra de alerta | 3000 |

Tópico de telemetria: `friocerto/abc/<loja>/telemetria/temperatura`

## Como executar

Pré-requisitos: Docker + Docker Compose e Python 3.

1. Subir a stack:
   ```bash
   docker compose up -d
   ```
2. Instalar a dependência e iniciar o produtor (14 sensores):
   ```bash
   pip install -r requirements.txt
   python produtor.py
   ```
3. Acessar o Grafana em http://localhost:3000 (usuário `admin`, senha `admin`).
4. Adicionar o data source **InfluxDB** (linguagem Flux):
   - URL: `http://influxdb:8086`
   - Organization: `friocerto`
   - Token: `dev-token-please-change`
   - Bucket padrão: `sensores`

## Dashboard e alerta

Consulta Flux usada no painel:

```flux
from(bucket: "sensores")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "temperatura_camara" and r._field == "temperatura")
  |> aggregateWindow(every: 2s, fn: mean, createEmpty: false)
  |> yield(name: "temperatura")
```

**Regra de alerta:** dispara quando `temperatura > 8.0` persistir por mais de 5 minutos (30 s no teste simulado).

## Validação da anomalia

O `produtor.py` injeta uma anomalia na **loja_07**: após 30 segundos de execução, as leituras passam para 11,5–13,5 °C. No dashboard, a série da loja_07 deve sair da faixa e o alerta deve disparar, enquanto as demais lojas permanecem entre 3,5 e 6,5 °C.

## Limitações para produção real

- **Comunicação insegura:** o broker opera sem TLS/mTLS na porta 1883 e com `allow_anonymous true`.
- **Ponto único de falha no InfluxDB:** sem clusterização ou replicação, há risco de perda do histórico regulatório.
- **Dependência de conexão centralizada:** sem edge gateways locais, leituras são perdidas durante quedas de telecomunicação nas lojas.
- **Credenciais de desenvolvimento:** senhas e token estão em texto no `docker-compose.yml`; em produção devem vir de secrets/variáveis de ambiente.

## Evolução (AF3/AF4)

- Apache Kafka para streaming e processamento de eventos complexos, com ingestão em data lake (Parquet/MinIO).
- Edge Machine Learning nos nós locais para inferência preditiva, antecipando violações do limiar de 8 °C a partir de padrões anormais de subida.

## Estrutura do repositório

```
.
├── docker-compose.yml
├── mosquitto/config/mosquitto.conf
├── telegraf/telegraf.conf
├── produtor.py
├── requirements.txt
├── docs/AF12-FrioCerto.md
└── README.md
```

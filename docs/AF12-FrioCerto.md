# AF12 — Atividade Formativa Integradora U1+U2: FrioCerto

**Disciplina:** Arquiteturas de Computação para IoT e Big Data (04803-80)
**Turma:** 493-02AN | **Professor:** Giovane de Morais
**Integrante:** João Victor Trindade Souza — RA 8169585

---

## PARTE A — Projeto Arquitetural

### A.1 — Modelagem dos Dados de Leitura de Temperatura

#### A.1.a) Escolha do Repositório de Dados

**Escolha:** InfluxDB (TSDB).

**Justificativa:** Os dados gerados pelas câmaras frias constituem séries temporais de alta frequência e carimbo contínuo. O InfluxDB oferece algoritmos de compressão de tempo e valor (baseados em Gorilla/TSI), políticas automatizadas de retenção e agregação eficiente em janelas temporais móveis (cálculo de médias, variância e desvio-padrão). Um SGBD relacional como o PostgreSQL introduziria custo computacional excessivo de indexação e gravação contínua ao longo de 5 anos sem necessidade de esquemas relacionais complexos, enquanto o armazenamento de arquivos Parquet em S3/MinIO elevaria a latência operacional das consultas dos dashboards em tempo real.

#### A.1.b) Schema (InfluxDB Line Protocol)

```text
# Measurement: temperatura_camara
# Tags: loja, regiao, sensor_id
# Fields: temperatura (float), humidade (float)
# Timestamp: epoch (nanossegundos)

temperatura_camara,loja=loja_01,regiao=santo_andre,sensor_id=camara_01 temperatura=4.5,humidade=55.2 1774000000000000000
```

#### A.1.c) Query para Q1 (minutos fora da faixa por loja no último mês)

```flux
from(bucket: "sensores")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "temperatura_camara" and r._field == "temperatura")
  |> filter(fn: (r) => r._value < 2.0 or r._value > 8.0)
  |> group(columns: ["loja"])
  |> count()
  |> map(fn: (r) => ({
      loja: r.loja,
      minutos_fora_da_faixa: r._value
  }))
```

### A.2 — Escolha do Rádio para os 14 Sensores

#### A.2.a) Matriz Comparativa de Tecnologias

| Critério | Wi-Fi 2,4 GHz da loja | LoRaWAN (Anatel Res. 680/2017) | NB-IoT (Operadoras) |
|---|---|---|---|
| **Custo mensal por sensor** | R$ 0,00 (rede existente) | R$ 0,00 (se gateway privado) | R$ 10,00 a R$ 20,00 por chip M2M |
| **Tolerância a queda do Wi-Fi** | Baixa | Alta | Alta |
| **Requer gateway próprio?** | Não | Sim | Não |
| **Latência típica** | < 50 ms | 1 a 5 s | 1 a 10 s |

#### A.2.b) Escolha e Justificativa

**Escolha:** Wi-Fi com buffer de contingência local no firmware do microcontrolador (ou NB-IoT como alternativa se houver orçamento de ~R$ 210/mês).

**Justificativa:** Considerando o orçamento estrito da rede e para evitar o custo de aquisição e instalação de 14 gateways LoRaWAN dedicados, o Wi-Fi aproveita a infraestrutura já paga. A vulnerabilidade às quedas de conexão em dias de tempestade é contornada dotando o microcontrolador de memória flash interna (SPIFFS/SD card) para retenção local (*store-and-forward*), reenviando o histórico com timestamp imediatamente após o restabelecimento da conectividade.

### A.3 — Protocolo de Aplicação e QoS

#### A.3.a) Escolha do Protocolo

**Escolha:** MQTT 5.0.

**Justificativa:** O padrão de publicação/assinatura desacopla os sensores dos sistemas de ingestão e visualização. O MQTT possui cabeçalho leve sobre TCP, suporte nativo a reconexão automática, mecanismos de Keep-Alive e distribuição simples de mensagens em múltiplos destinos simultâneos (TSDB, Grafana e serviços de alerta), superando o CoAP (UDP), que exigiria implementação manual de confiabilidade na camada de aplicação.

#### A.3.b) Política de QoS

- **Leituras normais (telemetria contínua):** QoS 0 (ou QoS 1). A perda pontual de uma medição a cada 60 s não descaracteriza a série temporal nem sobrecarrega a rede.
- **Alertas de temperatura fora de faixa (> 5 min):** QoS 1 (ou QoS 2). Garante a entrega obrigatória (*at least once*), assegurando que o operador de plantão receba o aviso sem risco de perda do pacote.

#### A.3.c) Topic Tree (Estrutura de Tópicos)

```text
friocerto/<regiao>/<loja>/<categoria>/<sensor_id>
```

Exemplos:

- Telemetria normal: `friocerto/abc/loja_01/telemetria/temperatura`
- Alerta crítico: `friocerto/abc/loja_01/alerta/temperatura`
- Inscrição matriz (todas as lojas do ABC): `friocerto/abc/+/telemetria/#`
- Inscrição individual (loja 07): `friocerto/abc/loja_07/#`

### A.4 — LGPD + Compliance Anvisa

#### A.4.a) Crachá RFID

**Classificação:** Dado pessoal comum. Trata-se de identificador cadastral/funcional numérico (matrícula) associado ao horário de abertura da porta, sem envolver características biológicas ou biométricas (Art. 5º, II da LGPD).

**Base legal:** Cumprimento de obrigação legal ou regulatória (Art. 7º, II) e execução de contrato de trabalho (Art. 7º, V), visando garantir a rastreabilidade do acondicionamento de insumos médicos exigida pela autoridade sanitária.

#### A.4.b) Câmera IP na Antessala

**Classificação:** A gravação contínua convencional em vídeo constitui dado pessoal comum. Apenas adquire status de dado biométrico sensível se for aplicada tecnologia de reconhecimento facial automatizado para extração de vetores biométricos.

**Base legal:** Legítimo interesse do controlador (Art. 7º, IX) ou exercício regular de direitos em contrato (Art. 11, II, "d").

**Medidas técnicas:** Política de expurgo periódico automático dos vídeos (15 a 30 dias na ausência de anomalias), delimitação estrita do campo de visão à entrada da câmara fria e controle rigoroso de perfis de acesso aos registros gravados.

#### A.4.c) Requisitos Técnicos da RDC 430/2020 da Anvisa

- **Integridade e não repúdio dos registros:** armazenamento seguro e imutável das medições, com trilha de auditoria e retenção contínua pelo período obrigatório de 5 anos.
- **Continuidade de monitoramento em falhas (buffer local e redundância):** capacidade de manter o registro das leituras durante falhas de fornecimento elétrico ou interrupção de conectividade, impedindo lacunas nas séries históricas.

---

## PARTE B — Laboratório Funcional em Docker Compose

Os arquivos desta parte estão na raiz do repositório:

- **B.1 — Stack:** `docker-compose.yml`, `mosquitto/config/mosquitto.conf`, `telegraf/telegraf.conf`
- **B.2 — Produtor Python (14 sensores com injeção de anomalia):** `produtor.py`
- **B.3 — Dashboard Grafana e regra de alerta:**

```flux
from(bucket: "sensores")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "temperatura_camara" and r._field == "temperatura")
  |> aggregateWindow(every: 2s, fn: mean, createEmpty: false)
  |> yield(name: "temperatura")
```

**Critério de alerta:** disparo quando `temperatura > 8.0` persistir por mais de 5 minutos (ou 30 s em teste simulado).

---

## PARTE C — Relatório e Reflexão

### C.1 — Documentação do Repositório

O `README.md` documenta a contextualização operacional para o monitoramento térmico das 14 filiais, o fluxo de dados (Sensor → Mosquitto → Telegraf → InfluxDB → Grafana), os parâmetros de execução via Docker Compose e a validação da anomalia induzida na filial 07.

### C.2 — Análise de Trade-offs: Limitações para Produção Real

- **Comunicação insegura:** o broker de desenvolvimento opera sem cifra SSL/TLS ou mTLS na porta 1883, inviável em rede aberta.
- **Ponto único de falha no InfluxDB:** a ausência de clusterização ou replicação de escrita expõe a organização ao risco de perda do histórico regulatório.
- **Dependência crítica de conexão centralizada:** a ausência de edge gateways locais para armazenamento intermediário causa descarte de dados durante interrupções de telecomunicações nas lojas.

### C.3 — Evolução da Arquitetura para AF3/AF4

A arquitetura poderá evoluir integrando barramentos de streaming escaláveis como Apache Kafka para processamento de eventos complexos e ingestão em data lakes (Parquet/MinIO). Adicionalmente, modelos de Edge Machine Learning nos nós locais permitirão inferência preditiva, antecipando violações do limiar de 8 °C a partir de padrões anormais de subida de temperatura.

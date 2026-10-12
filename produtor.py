import time
import json
import random
import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_BASE = "friocerto/abc"

# Compatível com paho-mqtt 1.x e 2.x
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()

client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_start()

lojas = [f"loja_{i:02d}" for i in range(1, 15)]
inicio = time.time()

while True:
    decorrido = time.time() - inicio

    for loja in lojas:
        # Anomalia: após 30s, a loja_07 passa a registrar temperatura fora da faixa
        if loja == "loja_07" and decorrido > 30:
            temperatura = round(random.uniform(11.5, 13.5), 2)
        else:
            temperatura = round(random.uniform(3.5, 6.5), 2)

        humidade = round(random.uniform(50.0, 65.0), 1)

        payload = {
            "loja": loja,
            "regiao": "abc",
            "temperatura": temperatura,
            "humidade": humidade,
            "timestamp": int(time.time())
        }

        topico = f"{TOPIC_BASE}/{loja}/telemetria/temperatura"
        client.publish(topico, json.dumps(payload), qos=0)

    time.sleep(2)

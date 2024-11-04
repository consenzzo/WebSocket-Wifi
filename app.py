from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os
from dotenv import load_dotenv
import subprocess
import sys
import threading
import time

# Importações para controle de volume no Windows
if sys.platform == 'win32':
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

load_dotenv()  # Carrega as variáveis do arquivo .env

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
socketio = SocketIO(app)

EXECUTABLE_PATH = os.getenv('EXECUTABLE_PATH')

def executar_executavel():
    if EXECUTABLE_PATH:
        try:
            subprocess.Popen([EXECUTABLE_PATH])
            print(f"Executável iniciado: {EXECUTABLE_PATH}")
        except Exception as e:
            print(f"Erro ao executar o arquivo: {e}")
    else:
        print("Caminho do executável não definido.")

def ajustar_volume_sistema(volume):
    if sys.platform == 'win32':
        from comtypes import CoInitialize
        CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
    
        # Converter o volume de porcentagem para o intervalo de 0.0 a 1.0
        volume_scalar = float(volume) / 100.0
        volume_interface.SetMasterVolumeLevelScalar(volume_scalar, None)
        print(f"Volume ajustado para {volume}%")
    else:
        print("Controle de volume não implementado para este sistema operacional.")

def obter_volume_sistema():
    if sys.platform == 'win32':
        from comtypes import CoInitialize, CoUninitialize
        CoInitialize()
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            volume_scalar = volume_interface.GetMasterVolumeLevelScalar()
            # Converter volume_scalar (0.0 a 1.0) para porcentagem (0 a 100)
            volume_percentage = int(volume_scalar * 100)
            return volume_percentage
        except Exception as e:
            print(f"Erro ao obter o volume atual: {e}")
            return None
        finally:
            CoUninitialize()
    else:
        print("Controle de volume não implementado para este sistema operacional.")
        return None

def monitorar_volume():
    if sys.platform == 'win32':
        volume_anterior = None
        
        while True:
            time.sleep(0.5)  # Verifica a cada 0.5 segundos
            from comtypes import CoInitialize, CoUninitialize
            CoInitialize()
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                volume_atual = int(volume_interface.GetMasterVolumeLevelScalar() * 100)
                if volume_anterior is None:
                    volume_anterior = volume_atual
                elif volume_atual != volume_anterior:
                    volume_anterior = volume_atual
                    print(f"Volume alterado para {volume_atual}%")
                    # Emite o evento para todos os clientes conectados
                    socketio.emit('volume_atualizado', {'volume': volume_atual})
            except Exception as e:
                print(f"Erro ao monitorar o volume: {e}")
            finally:
                CoUninitialize()
    else:
        print("Monitoramento de volume não implementado para este sistema operacional.")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('botao_clicado')
def handle_button_click(data):
    botao = data.get('botao')
    print(f"Botão {botao} clicado!")
    if botao == 2:
        executar_executavel()
    emit('resposta', {'mensagem': f"Você clicou no botão {botao}"}, broadcast=True)

@socketio.on('volume_mudou')
def handle_volume_change(data):
    volume = data.get('volume')
    print(f"Volume recebido: {volume}%")
    ajustar_volume_sistema(volume)
    emit('resposta', {'mensagem': f"Volume ajustado para {volume}%"}, broadcast=True)

@socketio.on('get_volume')
def handle_get_volume():
    volume = obter_volume_sistema()
    if volume is not None:
        emit('volume_atual', {'volume': volume})
    else:
        emit('volume_atual', {'volume': 50})  # Valor padrão se não for possível obter o volume

if __name__ == '__main__':
    threading.Thread(target=monitorar_volume, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)

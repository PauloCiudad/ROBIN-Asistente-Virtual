# Arquitectura

## Estructura del código

```
pyproject.toml            dependencias (uv), entrada `robin`
.python-version           3.12
src/robin/
  __main__.py             `python -m robin`
  app.py                  RobinController: une tray, atajo, ventana, IA; instancia única; cierre limpio
  onboarding.py           OnboardingController: nombre + 6 frases → variantes personales + huella de voz
  config.py               rutas en %APPDATA%\ROBIN, Settings (settings.json), logging
  autostart.py            iniciar con Windows (HKCU\...\Run)
  single_instance.py      QLocalServer: una segunda ejecución pide a la primera que se muestre
  hotkey.py               atajo global Win32 RegisterHotKey (Alt + X) + filtro de eventos nativos de Qt
  ai/
    chatgpt.py            ChatGPTService (QThread propio): login ChatGPT, conversación con streaming
    persona.py            instrucciones de personalidad de ROBIN (+ nombre del usuario, apps on/off)
    confirm.py            ConfirmationBroker: permiso del usuario para acciones de apps conectadas; parse_yes_no
  actions/
    tools.py              TOOL_SPECS (dynamicTools) + ActionRunner: valida y ejecuta open_app/open_url/open_path/find_files
    apps.py               AppIndex: Get-StartApps (caché 10 min), alias en español, lanzamiento por shell:AppsFolder
    files.py              carpetas conocidas (registro User Shell Folders), búsqueda de archivos, extensiones bloqueadas
    text_match.py         normalización y puntuación aproximada de nombres
  learning/
    activity.py           ActivityLog: SQLite local de eventos mínimos (retención 60 días)
    observers.py          AppObserver (app en primer plano, 5 s) y FileObserver (Recientes, 60 s)
    lnk.py                lector de .lnk (destino local)
    files_filter.py       qué archivos se aprenden (documentos, no programas ni carpetas del sistema)
    patterns.py           detect_patterns(): rutina de inicio del día, combinaciones de acciones
    automations.py        AutomationStore: scripts .py por plantilla, registro, ejecutar, posponer/descartar
    watcher.py            PatternWatcher: revisa cada 20 min y emite sugerencias
  voice/
    tts.py                TextToSpeech: edge-tts (Camila, Perú) → mp3 temporal → MCI; hilos síntesis + reproducción
    text.py               clean_for_speech (quita markdown/URLs/código) y SentenceSplitter (frases en streaming)
    stt.py                StreamingVAD (Silero), Transcriber (faster-whisper tiny/base), find_wake ("Oye Robin")
    listener.py           VoiceListener: micrófono → modos WAKE / COMMAND en hilo "robin-listen"
    chime.py              sonido de activación (wav generado)
    speaker.py            SpeakerProfile: huella de voz CAM++ (sherpa-onnx), umbral calibrado, variantes; save_samples
  ui/
    window.py             ventana glass abajo-izquierda: vista de asistente (sin historial), login, ajustes, onboarding
    onboarding.py         OnboardingPage: pasos, medidor de nivel del micro, nombre
    widgets.py            ToggleSwitch animado, icono generado por código
    glass.py              Acrylic + esquinas redondeadas + modo oscuro vía DWM (ctypes)
```

## Datos en el equipo (`%APPDATA%\ROBIN`)

| Ruta | Contenido |
|---|---|
| `settings.json` | ajustes/switches del usuario |
| `codex\` | CODEX_HOME propio: sesión de ChatGPT (tokens gestionados por el runtime de Codex) |
| `workspace\` | carpeta de trabajo de la IA (cwd del runtime) |
| `logs\robin.log` | log rotativo (sin contenido de conversaciones ni transcripciones) |
| `models\` | modelos Whisper tiny y base + CAM++ (huella de voz) (descarga única) |
| `activity.db` | registro de actividad para detectar rutinas (borrable desde Ajustes) |
| `patterns_state.json` | rutinas descartadas / pospuestas |
| `Documentos\ROBIN\automatizaciones\` | scripts `.py` generados + `automatizaciones.json` (fuera de %APPDATA%, visibles) |
| `voice\` | `profile.npy`/`profile.json` (huella, umbral, variantes) y `samples\*.wav` del entrenamiento |
| `tmp\` | mp3 temporales de la voz y `chime.wav` |

## Hilos y flujo

```
Hilo UI (Qt)                                Hilo "robin-ai"
─────────────                               ────────────────
Tray / Alt+X ──► RobinWindow.toggle()
RobinWindow.send_requested ──(cola)──────►  ChatGPTService.send()
                                              └─ Codex app-server (subproceso, JSON-RPC stdio)
RobinWindow.on_reply_delta  ◄──(cola)──────  reply_delta / reply_finished / state_changed
Botón Detener / Cancelar ──(directo)──────►  interrupt() / cancel_login()  (seguros entre hilos)
```

- Arranque: `ChatGPTService.start()` lanza el runtime con `CODEX_HOME` propio y lee la cuenta.
  Sin sesión → pantalla "Conecta tu cuenta de ChatGPT" → `login_chatgpt()` abre el navegador y espera.
- Conversación: hilo de Codex `ephemeral`, `Sandbox.read_only`, `ApprovalMode.deny_all`,
  `developer_instructions=PERSONA`, `Personality.friendly`, esfuerzo de razonamiento `low` (rapidez).
- Acciones: el hilo se crea con `dynamicTools=TOOL_SPECS`. Cuando el modelo llama una herramienta, el
  runtime envía `item/tool/call`; el hilo lector del SDK llama a `ChatGPTService._handle_server_request`,
  que delega en `ActionRunner.run()` y emite `action_performed` (aviso en el chat).
- Voz: el controlador pasa cada `reply_delta` por `SentenceSplitter`; cada frase completa va a
  `TextToSpeech.speak()`. Hilo de síntesis (edge-tts) → cola → hilo de reproducción (MCI). `stop()` sube un
  número de generación y todo lo pendiente se descarta. `speaking_changed` actualiza el estado "Hablando…".
- Escucha: `sounddevice` (16 kHz, bloques de 512) → cola → hilo "robin-listen". En modo WAKE el VAD corta
  tramos; los primeros 2 s se transcriben con Whisper tiny y `find_wake()` busca la frase. Si aparece:
  `wake_detected` (ventana + sonido + corta TTS) y la orden sale del tramo completo (Whisper base) o se graba
  en modo COMMAND. `command_recognized(text)` → `RobinWindow.submit_voice_text` → mismo flujo que escribir.
  `tts.speaking_changed` → `listener.set_strict` (mientras habla, solo "Oye Robin" completo).
- Permisos de apps: app conectada quiere escribir → runtime envía `mcpServer/elicitation/request` → hilo
  lector del SDK → `ConfirmationBroker.ask()` (bloquea) → `requested` → controlador: tarjeta + voz
  "¿Lo confirmo?" + micrófono → "sí"/"no"/botón → `resolve()` → respuesta `{action: accept|decline}`.
- Rutinas: ActionRunner → `on_action` → ActivityLog (si `observe_requests`); AppObserver/FileObserver →
  ActivityLog (según switches). PatternWatcher → `detect_patterns()` → `suggestion` → tarjeta + notificación →
  "Crear" → AutomationStore.create() (script por plantilla). `run_automation` → primera vez
  `ConfirmationBroker.ask()` → `AutomationStore.run()` (subproceso pythonw).
- Activación: Alt + X → `RobinController._on_hotkey` (visible → `dismiss()`; oculta → `show_window()` +
  micrófono). "Oye Robin" → verificación de hablante (si procede) → ventana + escucha. Al ocultarse,
  `hidden` → `ai.new_conversation` (sin historial).
- Onboarding: `ai.state_changed("ready")` con `onboarding_done=False` → `OnboardingController.start()`;
  pausa la palabra de activación, usa `listener.record_sample()` → `sample_recorded(audio, tiny, base)`.
- Cierre: `shutdown()` se encola en el hilo de IA, cierra Codex y termina el hilo; `tts.shutdown()` para la voz.

```
tests/                    pytest (`uv run pytest`)
packaging/
  robin.spec              PyInstaller (modo carpeta) → build\dist\ROBIN\ROBIN.exe
  robin.iss               Inno Setup → build\installer\ROBIN-Setup-<versión>.exe
  make_icon.py            genera robin.ico desde el icono dibujado por la app
  build.ps1               tests → icono → PyInstaller → instalador → SHA256
```

- Ocultarse sola: `reply_finished` → temporizador (500 ms) que espera a que termine la voz (+1,5 s) o un
  tiempo de lectura si la voz está apagada; no se oculta si hay permiso pendiente, sugerencia, ajustes,
  error, escucha activa, ratón encima o texto escrito (`auto_hide`, `blocks_auto_hide`, `user_engaged`).

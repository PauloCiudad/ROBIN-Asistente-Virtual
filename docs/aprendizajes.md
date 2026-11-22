# Aprendizajes

Lecciones no obvias, trampas y soluciones. Una entrada por aprendizaje, con fecha.

---

### 2026-11-21 — Porcupine (Picovoice) ya no sirve para un proyecto personal gratuito
Picovoice anunció que las AccessKeys del Free Tier dejaron de funcionar tras el 2026-06-30 y no hay plan
no comercial. Para la palabra de activación usar una opción open-source y local (p. ej. openWakeWord).

### 2026-11-21 — "Sign in with ChatGPT" no da acceso a voz
El acceso con la cuenta de ChatGPT vía Codex app-server sirve para texto/razonamiento. La API de voz de OpenAI
(TTS/Realtime/Whisper) requiere API key, así que STT y TTS deben resolverse con motores locales u otros servicios.

### 2026-11-21 — SDK `openai-codex`: detalles útiles
- `Codex(CodexConfig(env={..., "CODEX_HOME": ...}))` aísla la sesión de ROBIN de otras instalaciones de Codex.
- El manejador de aprobaciones por defecto del SDK **acepta** comandos y cambios de archivos. Por eso los hilos
  se crean con `ApprovalMode.deny_all` + `Sandbox.read_only` hasta tener una capa de acciones propia.
- `login_chatgpt().wait()` bloquea: va en el hilo de IA y se cancela desde otro hilo con `handle.cancel()`.
- Streaming: notificación `item/agentMessage/delta` (`payload.delta`, `payload.item_id`); fin en `turn/completed`.
- El arranque del runtime tarda ~5–8 s la primera vez.

### 2026-11-21 — Ventana glass en Qt sobre Windows 11
`FramelessWindowHint` + `WA_TranslucentBackground` + `SetWindowCompositionAttribute` (ACCENT_ENABLE_ACRYLICBLURBEHIND)
funciona, y `DWMWA_WINDOW_CORNER_PREFERENCE` redondea también el desenfoque. Hay que aplicarlo en el primer
`showEvent` (cuando ya existe el HWND).

### 2026-11-21 — Burbujas de chat con QLabel + wordWrap
Un QLabel con `wordWrap` dentro de un layout se encoge demasiado. Solución: fijar `minimumWidth` según el texto
(llamando antes a `ensurePolished()` para medir con la fuente de la hoja de estilos).

### 2026-11-21 — Notificaciones mostraban "Python"
Se arregla llamando `SetCurrentProcessExplicitAppUserModelID("ROBIN")` antes de crear la QApplication.

### 2026-11-21 — Voz: QtMultimedia no está en pyside6-essentials
Se usa MCI de Windows (`mciSendStringW ... type mpegvideo`) desde un hilo normal de Python; funciona sin COM
ni dependencias. Para cortar, consultar `status <alias> mode` en bucle y cerrar el alias.

### 2026-11-21 — Voz: cortar frases en streaming y bloques de código
Las marcas ``` pueden caer en el mismo trozo que la frase siguiente. Hay que partir el trozo por ``` y alternar
el modo código en cada marca; si no, se pierde la frase de después del bloque.

### 2026-11-21 — Voz: latencia de edge-tts
Cada `Communicate(...).save()` tarda ≈1,8 s (sobre todo en abrir la conexión). Por eso se habla frase a frase
mientras llega el texto en vez de esperar la respuesta completa.

### 2026-11-21 — Herramientas propias en Codex app-server
- No están en el SDK estable: se ven con `codex app-server generate-json-schema --experimental --out <dir>`
  (campo `dynamicTools` en `ThreadStartParams`, petición `item/tool/call`, respuesta `{contentItems, success}`).
- `client.thread_start()` acepta un dict, así que se añade `dynamicTools` al dump del modelo pydantic.
- Las features de Codex se listan con `codex features list` y se apagan con `-c features.<nombre>=false`
  (`CodexConfig.config_overrides`).
- En scripts de prueba sin `app.exec()`, las señales emitidas desde el hilo lector del SDK no llegan (van en cola).

### 2026-11-21 — Get-StartApps desde Python
PowerShell 5.1 devuelve texto en la página de códigos OEM: anteponer
`[Console]::OutputEncoding = [Text.Encoding]::UTF8;` al comando. Windows está en inglés → nombres como
"Calculator", "Notepad", "Settings"; por eso hay alias en español en `actions/apps.py`.

### 2026-11-21 — faster-whisper en CPU (i5-1235U)
- Sin `temperature=0.0`, los clips cortos tardan 3–5 s: Whisper reintenta con otras temperaturas cuando la
  confianza es baja. Con 0.0: "Oye Robin" en ~1 s (base) / ~0,7 s (tiny).
- `initial_prompt="Oye Robin."` evita transcripciones como "Hoy en Raven". Riesgo de alucinar el prompt en
  ruido: se mitiga con el VAD y filtrando `no_speech_prob`/`avg_logprob`.
- La primera transcripción tras cargar el modelo es muy lenta: hacer una en silencio al cargar.
- `faster_whisper.decode_audio` falla con PyAV reciente (`metadata_errors`); ROBIN no lo necesita (el micro
  da PCM). En pruebas, decodificar con `av` directamente.
- Silero VAD de faster-whisper (`SileroVADModel`) reinicia el estado en cada llamada; para streaming se usa la
  sesión ONNX directamente conservando `h`, `c` y los 64 samples de contexto.
- `WhisperModel(..., local_files_only=True)` evita consultar HuggingFace en cada arranque.

### 2026-11-22 — Empaquetado con PyInstaller
- `codex-code-mode-host.exe` y `codex-exec-server.exe` (del paquete `codex_cli_bin`) **son necesarios**:
  sin ellos, las herramientas propias (`find_files`…) y las apps conectadas fallan ("la herramienta no está
  disponible"), aunque el chat funcione.
- La SDK localiza codex.exe con `Path(codex_cli_bin.__file__).parent / "bin"`: basta copiar el paquete como
  datos en la misma ruta relativa dentro de `_internal`.
- En una app sin consola (`console=False`), `print()` no falla (no hace nada): las automatizaciones se pueden
  ejecutar con el propio ejecutable (`--run-script`).
- Verificación útil: `ROBIN.exe --run-script prueba.py` permite ejecutar diagnósticos dentro del entorno
  empaquetado (así se comprobó que la huella de voz da los mismos valores que en desarrollo).

### 2026-11-22 — "Oye Robin" en uso real
- Puntuaciones de verificación de la voz del usuario en vivo ≈0,55 (muestras de entrenamiento 0,82–0,89):
  el micrófono en vivo baja la similitud. Una voz ajena dio 0,01 (rechazada). Vigilar falsos rechazos.

### 2026-11-22 — Permisos de escritura de las apps conectadas
- Con `approval_policy="never"`, Codex rechaza en silencio las escrituras de apps ("esta sesión no permite
  aprobaciones"): no llega ninguna petición al cliente.
- La política granular (`{"granular": {"mcp_elicitations": true, ...}}`) permite que solo las apps pidan
  permiso vía `mcpServer/elicitation/request` (respuesta `{"action": "accept"|"decline", "content": {...}}`).
- El entorno de desarrollo (Claude Code) bloquea pruebas que escriben en el calendario real del usuario:
  la verificación de escritura la hace el usuario desde ROBIN.

### 2026-11-22 — Fase 3: detalles
- La carpeta Recientes de Windows tiene cientos de `.lnk`; ~70 % resuelven a ruta local con el lector propio
  (el resto: rutas de red, carpetas especiales).
- Al leer la salida de un subproceso Python en Windows, forzar `PYTHONIOENCODING=utf-8` y `encoding="utf-8"`.
- Al generar código con un heredoc de bash + Python, los `\n` dentro de cadenas pueden convertirse en saltos
  reales: para editar código con escapes, usar la herramienta de edición directamente.

### 2026-11-22 — Las apps conectadas en ChatGPT ya funcionan en ROBIN
La feature `apps` de Codex (activada por defecto; ROBIN no la apaga) expone los conectores que el usuario
tiene en su cuenta de ChatGPT. `app/list` (app-server) devuelve el catálogo con `isAccessible`: en la cuenta
del usuario están accesibles Google Calendar, Gmail, Canva, Figma, Sites, ChatGPT Space y AdAnalyze.
Prueba real: "¿cuántos eventos tengo hoy?" → ROBIN consultó Google Calendar y respondió (≈13,6 s).
Para añadir otra integración basta conectarla en ChatGPT (Ajustes → Apps). Pendiente: acciones de escritura
(crear eventos, enviar correos) — sin probar; el manejador de peticiones aún no atiende elicitaciones/aprobaciones
de herramientas MCP (responde `{}`).

### 2026-11-21 — Whisper corta la orden tras "Oye Robin."
Con `initial_prompt="Oye Robin."` y bastante silencio al final, Whisper base devolvía solo "Oye Robin." en
"Oye Robin, abre el navegador". Solución: recortar el silencio final (dejar 0,3 s) y usar para órdenes un
prompt que continúa ("Oye Robin, abre el navegador, por favor.").

### 2026-11-21 — Huella de voz
- Modelos de sherpa-onnx en el release `speaker-recongition-models` (sic, con la errata en la URL).
- Con voces sintéticas del mismo proveedor, dos hombres se parecen mucho (0,7–0,8); CAM++ zh_en dio el
  mejor margen. La frase nueva (no usada para el perfil) baja ~0,1 la similitud: por eso el umbral se
  calibra dejando una muestra fuera.
- Variantes personales de "Robin": exigir que empiecen por "r", o se aprende "bien" ("Oye, ¿bien?").

### 2026-11-21 — Pruebas de interfaz sin mostrar ventanas
`QT_QPA_PLATFORM=offscreen` permite simular flujos completos (onboarding) sin abrir ventanas en el escritorio.
`QTimer.singleShot` desde un hilo sin bucle de eventos no hace nada: disparar desde el bucle principal.

### 2026-11-21 — Medir un proceso lanzado desde .venv\Scripts\python.exe
Ese exe es un lanzador: el proceso real es un hijo. Buscar por línea de comandos (`-m robin`) y elegir el de
más memoria.

### 2026-11-21 — Python 3.15 es demasiado nuevo para el ecosistema de audio/IA
El PC tiene Python 3.15.0. Librerías como onnxruntime, faster-whisper o PySide6 suelen tardar en publicar
binarios para versiones nuevas. Si se usa Python, fijar 3.12/3.13 con `uv`.

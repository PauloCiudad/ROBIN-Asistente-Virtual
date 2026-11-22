# Registro de decisiones de arquitectura (ADR)

Formato de cada entrada:

```
## ADR-NNN — Título
- Fecha: AAAA-MM-DD
- Estado: Propuesta | Aceptada | Reemplazada por ADR-XXX
- Contexto: por qué hacía falta decidir
- Decisión: qué se decidió
- Consecuencias: qué implica (positivo y negativo)
```

---

## ADR-000 — Conexión a OpenAI solo mediante "Sign in with ChatGPT"

- Fecha: 2026-11-21
- Estado: Aceptada
- Contexto: el usuario no quiere usar API keys de ningún proveedor de IA; quiere usar su cuenta de ChatGPT (plan Plus).
- Decisión: usar el flujo oficial **"Sign in with ChatGPT"** de OpenAI a través del **Codex app-server**,
  controlado con el SDK oficial de Python `openai-codex`. El login se inicia con `Codex.login_chatgpt()`
  (`account/login/start` tipo `chatgpt`), que devuelve una URL que se abre en el navegador; el runtime
  guarda y refresca los tokens. ROBIN usa su propio `CODEX_HOME` (`%APPDATA%\ROBIN\codex`) para no mezclarse
  con otras instalaciones de Codex del usuario.
  OpenAI indica que el uso del plan de ChatGPT está pensado para apps *open-source y alojadas localmente*;
  una app personal local encaja en esa categoría. Para uso comercial o alojado habría que solicitarlo a OpenAI.
- Consecuencias:
  - (+) Sin API key, sin facturación por token; el uso consume los límites del plan Plus del usuario.
  - (−) Se depende del runtime de Codex (orientado a agentes de código): se configura como chat conversacional
    con instrucciones de desarrollador propias, sandbox de solo lectura y `ApprovalMode.deny_all`.
  - (−) La voz (STT/TTS) **no** está cubierta por este acceso; usa motores aparte (ADR-002).
  - (−) Está en *preview*; OpenAI puede cambiar condiciones o API. Toda la integración vive en
    `src/robin/ai/` detrás de una interfaz propia.

## ADR-001 — Lenguaje y stack principal: Python + PySide6

- Fecha: 2026-11-21
- Estado: Aceptada
- Contexto: ver [investigacion/stack-tecnologico.md](investigacion/stack-tecnologico.md). Opciones evaluadas:
  Python puro, Tauri + Python, Electron + TypeScript, C# WinUI 3.
- Decisión: **Opción A — Python 3.12 + PySide6 (Qt 6, QtWidgets)**.
  - Gestor de entorno y dependencias: `uv` (Python fijado en 3.12 con `.python-version`).
  - Código en `src/robin/` (layout `src`), punto de entrada `python -m robin`.
  - Tray: `QSystemTrayIcon`. Atajo global: `RegisterHotKey` de Win32 vía `ctypes` (no requiere admin ni hooks de teclado).
  - Ventana glass: ventana Qt sin bordes y translúcida + efecto Acrylic de DWM vía `ctypes`.
  - Instancia única: `QLocalServer`.
- Consecuencias:
  - (+) Un solo lenguaje; SDK oficial de ChatGPT, wake word, STT y TTS disponibles en Python.
  - (+) Los scripts que genere la detección de patrones corren en el mismo runtime.
  - (−) Ejecutable más pesado al empaquetar. El Python 3.15 del sistema no se usa (ecosistema sin binarios aún).

## ADR-002 — Voz de ROBIN: edge-tts con voz peruana

- Fecha: 2026-11-21
- Estado: Aceptada (implementada 2026-11-21)
- Contexto: el usuario quiere acento peruano y acepta que la voz use internet.
- Decisión: TTS con **edge-tts**, voz **`es-PE-CamilaNeural`** (mujer, español de Perú). Configurable en ajustes.
  Si en el futuro se necesita modo sin conexión, evaluar Kokoro/Piper como respaldo.
- Consecuencias: (+) voz natural, gratis, sin API key. (−) requiere internet; usa un endpoint no documentado
  de Microsoft que podría cambiar → aislar tras interfaz `TextToSpeech`.

## ADR-010 — Fase 3: aprendizaje de rutinas y automatizaciones en Python

- Fecha: 2026-11-22
- Estado: Aceptada (v1)
- Decisión:
  - **Registro local** `%APPDATA%\ROBIN\activity.db` (SQLite, retención 60 días, borrable desde Ajustes) con
    eventos mínimos: acciones de ROBIN (`observe_requests`), app en primer plano (`observe_apps`: solo
    ejecutable y ruta, cada 5 s, "abrir" = primera vez o tras 30 min sin usarla, ignora procesos del sistema)
    y archivos recientes (`observe_files`: carpeta Recientes de Windows, destino del `.lnk` con un lector
    propio, solo documentos fuera de AppData/Windows/Temp). No se guardan textos de peticiones, títulos de
    ventanas ni contenidos. Teclado: sigue "Próximamente" (sería un registro de teclas).
  - **Detección** (funciones puras, `learning/patterns.py`): (1) rutina de inicio del día — apps/archivos
    abiertos en los primeros 30 min en ≥3 días y ≥50 % de los últimos 7 días activos, ≥2 pasos;
    (2) combinaciones de acciones pedidas a ROBIN en una misma sesión (≥2 acciones) en ≥3 días.
    Revisión cada 20 min (primera a los 2 min) y bajo demanda.
  - **Sugerencia**: notificación + tarjeta en la ventana ("Crear automatización" / "Ahora no" = 3 días /
    "No volver a sugerir").
  - **Automatización** = script Python legible generado por plantilla (no por IA) en
    `Documentos\ROBIN\automatizaciones`, con `--dry-run`; registro `automatizaciones.json`.
  - **Ejecución**: herramientas `list_automations` / `run_automation` para el modelo; primera ejecución con
    permiso del usuario (reutiliza `ConfirmationBroker`); se ejecuta con el `pythonw` del entorno.
- Consecuencias: (+) scripts deterministas, revisables y editables; datos mínimos y locales. (−) Necesita
  varios días de uso para proponer algo; solo automatiza "abrir" (apps, archivos, webs) por ahora.

## ADR-009 — Apps conectadas de ChatGPT con permiso explícito del usuario

- Fecha: 2026-11-22
- Estado: Aceptada (lectura verificada; escritura implementada según el esquema, pendiente de prueba real)
- Contexto: la feature `apps` de Codex da acceso a los conectores de la cuenta de ChatGPT (Google Calendar,
  Gmail…). Con la política "never", Codex rechazaba cualquier escritura ("esta sesión no permite aprobaciones").
- Decisión:
  - Política de aprobación **granular**: `mcp_elicitations=True` (las apps pueden pedir permiso) y
    `sandbox_approval/rules/request_permissions/skill_approval=False` (todo lo demás se rechaza sin preguntar);
    `approvals_reviewer=user`.
  - `ConfirmationBroker` (`src/robin/ai/confirm.py`) atiende `mcpServer/elicitation/request` (modo form/url) e
    `item/tool/requestUserInput`: bloquea el hilo lector del SDK hasta que el usuario responde (botones
    "Sí, hazlo"/"No" o voz "sí/no", con 2 reintentos) o pasan 60 s (= no). Esc también rechaza.
    Formularios que piden datos libres obligatorios se rechazan (ROBIN no inventa datos). URLs solo https.
  - `item/permissions/requestApproval` → sin permisos extra; aprobaciones de comandos/archivos → `decline`.
  - Persona: antes de crear/cambiar/borrar/enviar, decir en una frase qué hará; no enviar correos a terceros
    sin petición explícita.
  - Switch **"Usar mis apps de ChatGPT"** (`use_chatgpt_apps`): apagado añade `features.apps=false` y reinicia
    el runtime de Codex (≈3 s).
- Consecuencias: (+) nada se crea/envía sin un "sí" del usuario. (−) La prueba real de escritura fue bloqueada
  por el sistema de permisos del entorno de desarrollo (escribe en el calendario real): la debe hacer el usuario.

## ADR-008 — Configuración inicial: nombre del usuario y entrenamiento de voz (huella CAM++)

- Fecha: 2026-11-21
- Estado: Aceptada
- Contexto: el usuario pidió que, tras conectar ChatGPT, ROBIN pregunte su nombre y aprenda su voz.
- Decisión:
  - `OnboardingController` (`src/robin/onboarding.py`) se lanza cuando la IA queda lista y
    `onboarding_done` es falso. Paso 1: ROBIN pregunta el nombre por voz (se puede escribir); se extrae con
    `extract_name()` y se confirma. Paso 2: 6 frases ("Oye Robin" ×3, tres órdenes) grabadas con el VAD.
  - Aprender la voz = (1) **variantes personales**: cómo transcribe Whisper tiny el "Robin" del usuario
    (solo palabras que empiezan por "r" y se parecen a "robin"); (2) **huella de voz** con el modelo
    **CAM++ zh_en** de 3D-Speaker vía `sherpa-onnx` (27 MB, ~0,2 s por muestra). Perfil = embedding medio;
    umbral = (similitud mínima dejando una muestra fuera − 0,25), acotado a [0,40; 0,60].
  - "Oye Robin" pasa por la verificación si el switch **"Solo responder a mi voz"** está activo y hay perfil.
    Alt + X y el botón de micrófono no verifican (el usuario está en el teclado).
  - Muestras WAV en `%APPDATA%\ROBIN\voice\samples` (futuro detector propio); perfil en `voice\profile.*`.
  - Se puede omitir el entrenamiento y repetirlo desde Ajustes → "Volver a entrenar mi voz".
- Alternativas evaluadas: wespeaker ResNet34 (EN) y NeMo TitaNet small: menor margen entre voces masculinas
  en pruebas con voces sintéticas.
- Consecuencias: (+) ROBIN llama al usuario por su nombre y no se activa con otras voces (prueba: voz
  entrenada 0,94; otra voz 0,43 → rechazada). (−) Umbral calibrado con voces sintéticas: con la voz real
  puede requerir ajuste (el log registra la puntuación de cada activación, sin audio ni texto).

## ADR-007 — ROBIN como asistente, no como chat

- Fecha: 2026-11-21
- Estado: Aceptada
- Decisión: la ventana (abajo a la izquierda, 420×440) muestra solo la última petición y su respuesta.
  Al ocultarse, la próxima llamada empieza una conversación nueva (`ChatGPTService.new_conversation`).
  Alt + X abre la ventana **ya escuchando** (micrófono activo); si está abierta, la oculta. Esc o la X dejan
  de escuchar y la mandan a la bandeja.
- Consecuencias: (+) experiencia de asistente de órdenes rápidas. (−) No hay seguimiento entre llamadas
  (si se quiere, se podría mantener el contexto unos minutos).

## ADR-006 — Escucha local: Silero VAD + Whisper (tiny para "Oye Robin", base para órdenes)

- Fecha: 2026-11-21
- Estado: Aceptada (v1). Revisar si el consumo de CPU con mucha conversación alrededor molesta.
- Contexto: openWakeWord exige entrenar un modelo propio para "Oye Robin" (horas, idealmente con GPU) y
  Porcupine ya no tiene plan gratuito. Se quería que funcionara ya, en español y sin enviar audio a internet.
- Decisión:
  - Micrófono con `sounddevice` a 16 kHz; **Silero VAD v6** (el ONNX que trae faster-whisper) en streaming
    para cortar tramos de voz (~0 % CPU en silencio).
  - Cada tramo de voz: se transcriben sus primeros 2 s con **Whisper tiny** (4 hilos, ~0,7–1 s) y se busca la
    frase con `find_wake()` (texto normalizado, variantes "Robin/Robbin/Rubin…", palabra de llamada
    "oye/hey/ok…"). Si aparece, el tramo completo se transcribe con **Whisper base** (8 hilos) para sacar la orden.
  - Si tras "Oye Robin" no hay orden, se graba hasta 1,1 s de silencio (máx. 20 s; 6 s sin voz = cancelar).
  - Mientras ROBIN habla, modo estricto: solo "Oye Robin" completo (su propia voz dice "Robin" a veces).
  - `temperature=0.0` + `initial_prompt="Oye Robin."`; se descartan tramos con `no_speech_prob ≥ 0.6` o
    `avg_logprob ≤ -1`.
  - Modelos en `%APPDATA%\ROBIN\models` (descarga única desde HuggingFace; luego `local_files_only`).
- Consecuencias: (+) funciona hoy, offline, en español, sin entrenar. (+) RAM medida ~160–220 MB en total.
  (−) Con gente hablando cerca, cada tramo cuesta ~1 s de CPU (medido 10–17 % de CPU total en esos ratos).
  (−) Latencia de activación ≈1–1,5 s tras terminar de hablar. Mejora futura (v2): modelo openWakeWord
  entrenado con muestras de la voz del usuario, dejando Whisper solo para las órdenes.

## ADR-005 — Acciones en el PC mediante herramientas propias ("dynamic tools"), sin terminal

- Fecha: 2026-11-21
- Estado: Aceptada
- Contexto: ROBIN debe abrir apps, archivos y webs. Codex trae una terminal (`shell_tool`) que permitiría
  ejecutar cualquier comando, y el manejador por defecto del SDK aprueba comandos y cambios de archivos.
- Decisión:
  - Se apagan las herramientas integradas con `-c features.shell_tool=false`, `computer_use`, `browser_use`,
    `browser_use_external` e `image_generation`.
  - ROBIN declara sus propias herramientas en `thread/start` → `dynamicTools` (campo experimental del
    app-server): `open_app`, `open_url`, `open_path`, `find_files` (`src/robin/actions/tools.py`).
  - El runtime pide ejecutarlas con la petición `item/tool/call`; ROBIN la atiende sustituyendo
    `codex._client._approval_handler` (atributo privado del SDK) y responde `{contentItems, success}`.
    Cualquier aprobación de comando o cambio de archivo se responde `decline`.
  - Validaciones: solo URLs http/https; `open_path` rechaza ejecutables y scripts; las apps se lanzan por
    `shell:AppsFolder\<AppID>` a partir de `Get-StartApps` (solo apps del menú Inicio).
  - Todas consultan en caliente el switch `allow_open_apps`.
- Consecuencias: (+) superficie de acción pequeña y auditable; (+) el switch se respeta sin reiniciar.
  (−) `dynamicTools` y el reemplazo del manejador dependen de APIs experimentales/privadas del SDK: al
  actualizar `openai-codex`, volver a probar (`tests/test_actions.py` + prueba real "abre la calculadora").

## ADR-004 — Reproducción de audio con MCI de Windows (no QtMultimedia)

- Fecha: 2026-11-21
- Estado: Aceptada
- Contexto: QtMultimedia no viene en `pyside6-essentials`; requiere `pyside6-addons` (cientos de MB).
- Decisión: reproducir los mp3 de edge-tts con **MCI** (`winmm.mciSendStringW`, tipo `mpegvideo`) vía `ctypes`,
  desde un hilo propio que consulta el estado cada 40 ms (permite cortar al instante con `stop()`).
- Consecuencias: (+) cero dependencias extra, nativo de Windows. (−) solo Windows (aceptable: el proyecto es
  solo Windows); se trabaja con archivos temporales en `%APPDATA%\ROBIN\tmp`.

## ADR-003 — Permisos de observación y acciones controlados por switches

- Fecha: 2026-11-21
- Estado: Aceptada
- Contexto: la detección de patrones puede observar distintas fuentes con distinto impacto en privacidad, y
  ROBIN podrá abrir apps/archivos del PC. El usuario quiere decidir cada cosa desde la interfaz.
- Decisión: la ventana de ROBIN tiene un panel de **Ajustes** con un switch por cada capacidad sensible:
  - Aprendizaje de patrones: *lo que le pido a ROBIN* (activado por defecto), *apps que uso*, *archivos que abro*,
    *teclado* (estos tres desactivados por defecto).
  - Acciones: *abrir apps, archivos y webs* (activado por defecto).
  - Voz: *voz de ROBIN*, *escuchar "Oye Robin"*.
  - General: *iniciar con Windows*.
  Los ajustes se guardan en `%APPDATA%\ROBIN\settings.json`. Cada módulo consulta su switch antes de actuar.
- Consecuencias: (+) el usuario controla qué se observa. (−) cada módulo debe respetar los cambios en caliente.

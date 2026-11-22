# Estado actual

**Última actualización:** 2026-11-21
**Fase:** 2 — Voz y acciones (completa) → siguiente: Fase 3

## Hecho

- 2026-11-21 — `CLAUDE.md`, `GEMINI.md`, `AGENTS.md` (idénticos) y estructura de `docs/`.
- 2026-11-21 — Investigación de stack y decisiones ADR-000 a ADR-003 (Python + PySide6, login ChatGPT,
  voz `es-PE-CamilaNeural`, switches de permisos).
- 2026-11-21 — Proyecto inicializado: git (rama `main`), `uv`, Python 3.12, layout `src/robin`.
- 2026-11-21 — Fase 1 implementada y verificada en el PC del usuario:
  - Icono en la bandeja con menú (Abrir, Ajustes, Salir) y notificación de bienvenida.
  - Instancia única.
  - Alt + X global (probado con pulsación simulada) muestra/oculta la ventana.
  - Ventana glass (Acrylic de DWM, esquinas redondeadas, modo oscuro), arrastrable, Esc oculta.
  - Login "Sign in with ChatGPT": el usuario inició sesión; detecta plan **plus**.
  - Chat con streaming verificado (respuesta real de ROBIN en español).
  - Panel de ajustes con switches (ADR-003). Solo "Iniciar con Windows" tiene efecto hoy; los demás se
    guardan y llevan la etiqueta "Próximamente".

- 2026-11-21 — **Voz de ROBIN** (Fase 2, paso 1) implementada y verificada:
  - edge-tts `es-PE-CamilaNeural` + reproducción MCI (ADR-004), en `src/robin/voice/`.
  - Habla frase a frase mientras llega la respuesta (≈5–6 s desde el envío hasta oír la voz, casi todo es
    latencia de ChatGPT; cada frase tarda ≈1,8 s en sintetizarse).
  - Limpia markdown, URLs y bloques de código antes de hablar.
  - Switch "Voz de ROBIN" activo + botón de altavoz en la cabecera (silenciar/activar).
  - Estado "Hablando…"; el botón Detener corta respuesta y voz; nueva respuesta o nueva conversación cortan la voz.
  - Tests: `tests/test_voice_text.py` (4 tests, `uv run pytest`).

- 2026-11-21 — **Abrir apps, archivos y webs** (Fase 2, paso 2) implementado y verificado (ADR-005):
  - Herramientas `open_app`, `open_url`, `open_path`, `find_files` en `src/robin/actions/`.
  - Terminal de Codex desactivada: el modelo respondió que no tiene acceso a la terminal.
  - Prueba real: "Abre la calculadora" → abrió Calculator (alias español → nombre en inglés).
  - Aviso en el chat ("↗ Abriendo Calculator"); switch "Abrir apps, archivos y webs" activo.
  - Tests: `tests/test_actions.py` (9 tests). Total: 13 tests.

- 2026-11-21 — **Escucha: "Oye Robin" + dictado** (Fase 2, paso 3) implementado y verificado (ADR-006):
  - `src/robin/voice/stt.py` (VAD en streaming, Transcriber, `find_wake`) y `voice/listener.py`.
  - Botón de micrófono en la ventana; estados "Escuchando…" / "Entendiendo…"; sonido de activación (`voice/chime.py`).
  - "Oye Robin" muestra la ventana, corta la voz de ROBIN y escucha; "Oye Robin, abre Excel" de corrido
    envía la orden directamente.
  - Switch "Escuchar Oye Robin" activo (abre/cierra el micrófono en caliente).
  - Simulación con audio sintético: 4/4 escenarios correctos (orden seguida, con pausa, sin activación, ruido).
  - En el PC real se registraron activaciones y una orden que abrió una web (probablemente pruebas del usuario).
  - Medido: RAM 160–220 MB (+ ~70 MB del runtime de Codex); CPU 10–17 % mientras había voz cerca.
  - Tests: `tests/test_wake.py` (10 casos). Total: 23 tests.

- 2026-11-21 — **Cambios pedidos por el usuario** (ADR-007 y ADR-008), implementados y verificados:
  - Ventana abajo a la izquierda; vista de asistente sin historial (última petición + respuesta); cada
    llamada empieza conversación nueva.
  - Alt + X abre ya escuchando; Esc/X deja de escuchar y va a la bandeja.
  - Configuración inicial tras conectar ChatGPT: nombre (por voz o escrito) + 6 frases de entrenamiento
    → variantes personales + huella de voz (CAM++/sherpa-onnx). Switch "Solo responder a mi voz".
  - Ajustes → "Tu perfil": cambiar nombre y "Volver a entrenar mi voz".
  - ROBIN usa el nombre del usuario (persona + saludo "Hola, Paulo. ¿En qué te ayudo?").
  - Simulación completa del onboarding (ventana offscreen, voz sintética): nombre "Paulo" extraído de
    "Me llamo Paulo", 6/6 frases, perfil creado (umbral 0,53), verificación: voz entrenada 0,94 ✔, otra 0,43 ✘.
  - Corrección: Whisper base cortaba "Oye Robin, abre el navegador" tras "Oye Robin." → se recorta el
    silencio final y el modelo de órdenes usa un prompt con continuación.
  - Tests: 30 (nuevos: nombre, variantes personales).

- 2026-11-22 — Descubierto: las **apps conectadas en ChatGPT** (Google Calendar, Gmail, Canva, Figma…) ya
  están disponibles en ROBIN vía la feature `apps` de Codex. Lectura de Google Calendar verificada.
  Sin probar: escritura (crear eventos, enviar correos) y su confirmación.

- 2026-11-22 — El usuario completó la configuración inicial con su voz real (6 muestras, LOO mín. 0,75,
  umbral 0,50). "Escuchar Oye Robin" sigue apagado por decisión del usuario.
- 2026-11-22 — **Permisos para apps conectadas + switch** (ADR-009): política granular, `ConfirmationBroker`
  (tarjeta "Necesito tu permiso" + voz sí/no + 60 s), switch "Usar mis apps de ChatGPT".
  Verificado: lectura del calendario con la nueva política (12,5 s); con el switch apagado ROBIN dice que
  están desactivadas. **Sin verificar:** crear un evento real (bloqueado en desarrollo; lo prueba el usuario).
  Tests: 47.

- 2026-11-22 — **Fase 3: rutinas → automatizaciones Python** (ADR-010), implementada y verificada:
  - `src/robin/learning/`: `activity.py` (SQLite), `observers.py` (app en primer plano, Recientes),
    `lnk.py` (destino de accesos directos), `patterns.py` (detección), `automations.py` (scripts y registro),
    `watcher.py` (revisión periódica y sugerencias).
  - Tarjeta "Noté una rutina…", sección Ajustes → Automatizaciones (abrir carpeta, buscar ahora, borrar).
  - Herramientas del modelo `list_automations` / `run_automation` (primera ejecución con permiso).
  - Verificado en el PC: lector .lnk resuelve 234/324 recientes (101 documentos aprendibles); detección de
    app en primer plano OK. Tests: detección, script generado compila y `--dry-run` lista los pasos,
    aprobación de la primera ejecución. Total 55 tests.
  - Los switches "Apps que uso" y "Archivos que abro" siguen **apagados** (por defecto): el usuario decide.

## En curso

- Nada en curso.

## Próximos pasos

1. Que el usuario pruebe crear un evento real (confirmación) y active los switches de aprendizaje si quiere.
2. Tras unos días de uso, revisar las rutinas detectadas y ajustar umbrales.
3. Ideas: automatizar más que "abrir" (p. ej. pedir a ChatGPT un resumen diario), "Oye Robin" v2, empaquetado.

## Pendientes / mejoras conocidas

- "Oye Robin" v2: modelo openWakeWord entrenado con muestras de la voz del usuario (menos CPU).
- Medir CPU en silencio total (no se pudo: había voz cerca durante la medición).
- Interrumpir a ROBIN con la voz mientras habla funciona solo en modo estricto ("Oye Robin" completo).
- Pocos tests de interfaz.
- Acciones futuras: cerrar apps, controlar volumen/multimedia, crear/mover archivos (requieren ADR y confirmación).
- Latencia de voz: se podría sintetizar en paralelo o usar `Communicate.stream()` para ganar ~1 s.
- Elegir voz (Camila / Alex) desde Ajustes.
- El atajo Alt + X no es configurable aún.
- Empaquetado como .exe (Fase 5).

## Entorno

- Windows 11 Home 10.0.26300 · uv 0.13.8 · git 2.55
- Python del proyecto: 3.12 (`.venv`). El sistema tiene 3.15 (no usar para este proyecto).
- Hardware: i5-1235U (10 núcleos / 12 hilos), 7,7 GB RAM, micrófono Realtek integrado.
- Dependencias clave: pyside6-essentials 6.12.0, openai-codex 0.171.0, edge-tts 7.3.1, faster-whisper,
  sounddevice, numpy, sherpa-onnx 2.0.2 (dev: pytest).

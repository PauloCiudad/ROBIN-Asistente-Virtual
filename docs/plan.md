# Plan / hoja de ruta

## Fase 0 — Fundamentos ✅

- [x] Crear `CLAUDE.md`, `GEMINI.md`, `AGENTS.md` y la carpeta `docs/`.
- [x] Investigar lenguajes y librerías posibles → [investigacion/stack-tecnologico.md](investigacion/stack-tecnologico.md).
- [x] Decidir el stack con el usuario (ADR-001: Python + PySide6).
- [x] Confirmar requisitos abiertos (plan Plus, acento peruano, internet permitido, switches de permisos).
- [x] Inicializar repositorio git, estructura de carpetas, gestor de dependencias y `.gitignore`.

## Fase 1 — Esqueleto ✅

- [x] App en la bandeja del sistema (icono, menú: Abrir, Ajustes, Salir).
- [x] Instancia única (no abrir dos ROBIN a la vez).
- [x] Arranque automático con Windows (switch en Ajustes).
- [x] Atajo global **Alt + X** que muestra/oculta la ventana.
- [x] Ventana pequeña estilo *glass* (Acrylic de Windows 11), siempre encima, con campo de texto y respuestas.
- [x] Primer arranque: flujo **"Sign in with ChatGPT"** (OAuth en navegador); sesión persistida por el runtime.
- [x] Chat por texto con ChatGPT con respuestas en streaming.
- [x] Panel de ajustes con switches por permiso (ADR-003); cerrar sesión desde Ajustes.

## Fase 2 — Voz y acciones ✅

- [x] Texto → voz con edge-tts, voz `es-PE-CamilaNeural` (switch "Voz de ROBIN").
- [x] Abrir apps, archivos y webs del PC (switch "Abrir apps, archivos y webs").
- [x] Palabra de activación local "Oye Robin" (switch "Escuchar Oye Robin") — v1 con Whisper tiny (ADR-006).
- [x] Voz → texto (STT) en español (Whisper base local) + botón de micrófono.
- [x] Indicador visual de "escuchando / entendiendo / pensando / hablando".
- [ ] (Mejora) "Oye Robin" v2 con modelo openWakeWord entrenado con la voz del usuario.

## Fase 2.5 — Ajustes de experiencia ✅

- [x] Ventana abajo a la izquierda, sin historial (asistente, no chat).
- [x] Alt + X abre escuchando; Esc deja de escuchar y va a la bandeja.
- [x] Configuración inicial: nombre del usuario + entrenamiento de voz (variantes + huella de voz).
- [x] "Solo responder a mi voz" y "Volver a entrenar mi voz" en Ajustes.
- [x] Posibilidad de interrumpir a ROBIN mientras habla (botón Detener / altavoz).

## Fase 3 — Automatización por patrones ✅ (v1)

- [x] Observadores locales según switches: acciones de ROBIN, apps usadas, archivos abiertos.
- [ ] Teclado (pendiente: requiere un diseño de privacidad muy cuidadoso).
- [x] Detección de patrones repetitivos (rutina de inicio del día; combinaciones de acciones).
- [x] Generación de scripts Python en `Documentos\ROBIN\automatizaciones`, revisables y con `--dry-run`.
- [x] Confirmación antes de la primera ejecución; automatizaciones invocables por voz.

## Fase 4 — Integraciones

- [ ] Google Calendar (OAuth de Google): consultar, crear y mover eventos.
- [ ] Nuevas funciones según indique el usuario.

## Fase 5 — Distribución

- [ ] Empaquetado como ejecutable/instalador para Windows.
- [ ] Actualizaciones.

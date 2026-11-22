# Reglas del proyecto

Estas reglas son obligatorias para cualquier persona o agente de IA que trabaje en el repositorio.

## 1. Documentación

- `docs/` es la fuente única de verdad. Si algo no está aquí, no está decidido.
- `CLAUDE.md`, `GEMINI.md` y `AGENTS.md` (en la raíz) deben ser **idénticos**. Cualquier cambio se replica en los tres.
- Al cerrar una tarea:
  - Actualizar [estado.md](estado.md) (qué se hizo, qué sigue).
  - Registrar decisiones de arquitectura en [decisiones.md](decisiones.md) con el formato ADR indicado allí.
  - Registrar trampas, bugs raros o soluciones no obvias en [aprendizajes.md](aprendizajes.md).
- Las fechas se escriben en formato absoluto `AAAA-MM-DD`.

## 2. Idioma

- Documentación, textos de la interfaz, mensajes al usuario y voz de ROBIN: **español**.
- Identificadores de código (variables, funciones, clases, archivos): **inglés**.
- Comentarios: español, solo cuando expliquen el *porqué*.

## 3. Inteligencia artificial y credenciales

- **Prohibido usar API keys** de OpenAI u otros proveedores de IA. La conexión a OpenAI es exclusivamente
  mediante "Sign in with ChatGPT" (OAuth) con la cuenta del usuario.
- Tokens OAuth y cualquier secreto se guardan fuera del repositorio (almacén seguro del sistema, p. ej.
  Windows Credential Manager, o la ubicación gestionada por el runtime de Codex). Nunca en código, logs ni commits.
- `.env`, archivos de credenciales y tokens deben estar en `.gitignore`.

## 4. Privacidad

- La escucha permanente de la palabra de activación debe ser **100 % local**. No se envía audio a ningún
  servicio hasta que se detecta "Oye Robin" o se pulsa Alt + X.
- La detección de patrones registra solo lo mínimo necesario, de forma local, y el usuario debe poder verlo y borrarlo.
- Las muestras de voz y la huella de voz del usuario (`%APPDATA%\ROBIN\voice`) nunca salen del PC ni van al repo.
- Los logs no guardan audio, transcripciones ni contenido de conversaciones (solo eventos y puntuaciones).
- Los scripts generados automáticamente **no se ejecutan sin confirmación** del usuario la primera vez.
- Las apps conectadas (Calendar, Gmail…) **nunca** crean, cambian, borran ni envían nada sin un "sí" explícito
  del usuario (ver ADR-009).
- El registro de actividad no guarda textos de peticiones, títulos de ventanas ni contenidos de archivos.

## 5. Código

- Seguir el stack registrado en [decisiones.md](decisiones.md). No cambiarlo ni agregar dependencias
  relevantes sin un ADR.
- Arquitectura modular: cada capacidad (tray, hotkey, wake word, STT, TTS, IA, patrones, integraciones) en su
  propio módulo con interfaz clara, para poder reemplazar implementaciones.
- El proceso en reposo debe consumir poca CPU y RAM (objetivo: < 3 % CPU y < 250 MB RAM escuchando).
- Manejo de errores visible para el usuario: si algo falla (sin micrófono, sesión expirada, sin internet),
  ROBIN lo dice con claridad y no se cae.

## 6. Git

- Commits pequeños y descriptivos en español.
- No hacer commit de secretos, audio grabado del usuario ni modelos binarios pesados sin acordarlo.

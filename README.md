# Soul Arena — Grupo 8

Prototipo de shooter 2D en Python y Pygame-ce para probar la jugabilidad antes de diseñar los gráficos finales.

## Ejecutar en Windows

Se necesita Python 3.11 o posterior. Abrir `INICIAR_JUEGO.cmd`: la primera vez crea el entorno e instala Pygame-ce (requiere internet), y después inicia el juego.

También se puede configurar manualmente desde la carpeta del proyecto:

```bash
py -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe main.py
```

Si Python está disponible como `python` en vez de `py`, usar `python -m venv .venv`.

## Controles

| Acción | Control |
|---|---|
| Mover | WASD |
| Apuntar | Mouse |
| Disparar | Clic izquierdo sostenido |
| Comprar habilidades | TAB |
| Mapa de zonas | M |
| Pausar / continuar | P |
| Volver de una pantalla | Esc |
| Reiniciar después de victoria o derrota | R |

Defender el guardián verde y sobrevivir tres oleadas para completar una zona. Los enemigos rojos avanzan siempre hacia el guardián: rodean paredes mediante rutas BFS y disparan al jugador si está a menos de 330 píxeles y tienen línea de visión. No lo persiguen ni abandonan su ruta para buscarlo. A 115 píxeles del guardián, con visión directa, se detienen y quedan fijados a él: ya no cambian de objetivo aunque el jugador se acerque.

Las paredes bloquean personajes, visión y balas de ambos bandos. Los disparos enemigos son rojos y pueden dañar al jugador o al guardián según con quién choquen primero. Los enemigos con un aro amarillo ya están atacando al guardián. Los círculos oscuros marcan las entradas de enemigos. No hay fuego amigo entre minions. Las balas usan comprobaciones de todo el segmento recorrido para no atravesar paredes o personajes entre fotogramas.

La segunda versión aumenta cantidad, frecuencia, vida y velocidad de los enemigos. El mapa tiene pasillos y cobertura provisionales inspirados en un shooter de vista superior; todas las zonas reutilizan la misma geometría por ahora. Cada baja otorga almas. Completar una zona da 15 almas adicionales y habilita la compra de sus rutas. Comprar una ruta descuenta su costo una sola vez. Las zonas desbloqueadas se pueden volver a jugar sin costo para ganar más almas.

TAB y M detienen el combate. Viajar o repetir una zona reinicia sus oleadas y restaura la vida del jugador y el guardián; conserva almas, habilidades y zonas desbloqueadas. Una derrota requiere reiniciar la partida completa. Completar el Núcleo termina la partida con victoria.

## Estructura actual

- `main.py`: punto de entrada.
- `game/app.py`: pantallas, interfaz, oleadas y coordinación del prototipo.
- `game/entities.py`: jugador, enemigos y balas.
- `game/world.py`: paredes, colisiones, línea de visión y rutas BFS de los enemigos.
- `game/progression.py`: árbol binario de habilidades y grafo dirigido ponderado, independientes de Pygame.

El árbol no es un ABB: representa prerrequisitos, no orden por claves. El grafo usa listas de adyacencia y muestra un recorrido BFS en la pantalla del mapa. Los nombres, precios, estadísticas y posiciones son provisionales. El prototipo no tiene guardado, sonido, recursos gráficos externos ni multijugador.

## Trabajo en equipo

`main` conserva versiones estables; `develop` integra el desarrollo. Cuando un compañero tome una tarea, crea una rama desde `develop` y presenta un pull request hacia ella. Este primer prototipo concentra la interfaz para facilitar cambios de funcionalidad; se separará en más módulos cuando se estabilice la jugabilidad.

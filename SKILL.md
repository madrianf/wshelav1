# Guía de Skills (Habilidades)

Este documento describe la estructura y el proceso para agregar nuevas "skills" (habilidades o funcionalidades modulares) a este proyecto.

## Estructura de Carpetas

La estructura recomendada para organizar las habilidades es la siguiente:

```text
skills/
├── README.md               # Instrucciones específicas de la carpeta
├── common/                 # Funciones y utilidades compartidas entre skills
├── <nombre_de_la_skill>/   # Carpeta por cada habilidad específica
│   ├── main.py             # Lógica principal de la skill
│   ├── utils.py            # Utilidades propias de la skill
│   └── requirements.txt    # Dependencias específicas si fuera necesario
└── templates/              # Plantillas para crear nuevas skills
```

## Cómo Crear una Nueva Skill

1. **Crear la Carpeta**: Crea una nueva subcarpeta dentro de `skills/` con el nombre de tu funcionalidad.
2. **Definir la Lógica**: Implementa la funcionalidad principal en `main.py`.
3. **Documentar**: Añade un pequeño `README.md` dentro de la carpeta de la skill explicando qué hace y cómo se usa.
4. **Integración**: Registra o importa la skill en el flujo principal de la aplicación (`app.py` o similar).

## Buenas Prácticas

- **Modularidad**: Cada skill debe ser lo más independiente posible.
- **Manejo de Errores**: Implementa bloques try-except para evitar que un fallo en una skill afecte a toda la app.
- **Documentación**: Mantén actualizado este archivo y los README locales.

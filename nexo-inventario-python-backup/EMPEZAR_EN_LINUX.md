# Llevar Nexo Inventario a CachyOS

## Qué contiene esta entrega

Código completo de la versión creada en Windows, interfaz, pruebas, documentación y un lanzador para Linux. No contiene ejecutables de Windows, entornos virtuales, paquetes instalados, credenciales ni bases de datos. Esta entrega debe extraerse en una carpeta nueva, sin sobrescribir el proyecto creado en CachyOS.

## Abrirlo

1. Lleva `Nexo-para-Linux.zip` a CachyOS mediante una carpeta accesible desde ambos sistemas, un USB o el método que uses habitualmente.
2. Extrae el ZIP con el gestor de archivos. Se creará `nexo-desde-windows`.
3. Abre una terminal dentro de esa carpeta y ejecuta:

```bash
bash iniciar-linux.sh
```

Necesita Python 3.10 o posterior. El servidor y la interfaz no requieren instalar dependencias con pip o npm. No es necesario ejecutar el lanzador de escritorio Tkinter ni el empaquetador Windows.

Abre http://127.0.0.1:8766 si el navegador no se abre automáticamente. Usa 8766 para evitar el puerto 8765 de otra versión que pudiera estar ejecutándose. Si 8766 ya está ocupado:

```bash
NEXO_PORT=8770 bash iniciar-linux.sh
```

La base nueva se guarda en `data/nexo.sqlite3` dentro de esta copia. Empieza vacía: puedes crear una empresa o explorar una demo. Conserva la terminal abierta mientras trabajas. Ctrl+C detiene el servidor.

## Llevar también los datos de Windows (opcional)

Junto al ZIP se entrega `nexo-datos-windows.sqlite3`, una instantánea consistente de la base de desarrollo usada en esta conversación. No es el código de CachyOS ni una mezcla de bases. Puede contener datos añadidos en esta copia local; trátalo como información privada y no lo subas a Git.

Para abrir ese respaldo sin tocar datos existentes:

1. Detén esta copia de Nexo si está abierta.
2. Crea una carpeta NUEVA y VACÍA llamada `datos-importados-windows` dentro de `nexo-desde-windows`.
3. Copia el respaldo a esa carpeta y cambia únicamente el nombre de esa copia a `nexo.sqlite3`. No sobrescribas ningún archivo existente.
4. Desde `nexo-desde-windows`, ejecuta:

```bash
NEXO_DATA_DIR="$PWD/datos-importados-windows" bash iniciar-linux.sh
```

El ZIP y el respaldo deben trasladarse antes de abandonar Windows si no puedes acceder a sus archivos desde CachyOS.

## Continuar con el agente de Linux

Abre `nexo-desde-windows` como carpeta del proyecto y pega el texto de `PARA_EL_AGENTE_LINUX.md`. Ahí están el objetivo, los archivos principales, las pruebas realizadas y los límites conocidos. El agente deberá localizar y comparar el otro proyecto antes de elegir qué integrar.

No necesitas volver a pedir que cree otro inventario desde cero.

## Comprobar esta copia

```bash
python3 -m unittest discover -s tests -v
```

Si Node está instalado, también puedes ejecutar `node --check static/app.js`; Node no es necesario para usar la aplicación. La prueba `tests/smoke_distribution.py` corresponde al ejecutable Windows y no debe ejecutarse en Linux.

La entrega y sus pruebas se verificaron en Windows. La ejecución real en CachyOS y el lanzador Bash quedan por verificar allí; no se afirma que ya hayan sido probados en Linux.

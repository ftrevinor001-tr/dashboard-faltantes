# 📊 Dashboard Faltantes — Sin instalar nada

Todo se hace desde el navegador. Sin Python, sin programas.

---

## CONFIGURACIÓN INICIAL (una sola vez, ~20 minutos)

### 1️⃣  Crear cuenta en GitHub
👉 Ve a **https://github.com/signup** y crea una cuenta gratuita.

---

### 2️⃣  Crear el repositorio
1. Inicia sesión en GitHub
2. Clic en el botón verde **"New"** o ve a https://github.com/new
3. Rellena:
   - **Repository name:** `dashboard-faltantes`
   - **Visibility:** ✅ **Public**
4. Clic en **"Create repository"**

---

### 3️⃣  Subir los archivos del repositorio
En la página de tu nuevo repositorio:

1. Clic en **"uploading an existing file"** (o "Add file → Upload files")
2. **Arrastra toda la carpeta** del repositorio que te entregó Claude:
   - `index.html`
   - `.github/workflows/actualizar.yml`
   - `scripts/procesar_datos.py`
   - `data/SUBE_AQUI_EL_EXCEL.txt`

   > ⚠️ Los archivos dentro de `.github/` y `scripts/` deben mantener su estructura de carpetas

3. Clic en **"Commit changes"**

---

### 4️⃣  Activar GitHub Pages (tu URL pública)
1. En tu repositorio → pestaña **Settings**
2. En el menú izquierdo: **Pages**
3. En "Source": selecciona **"Deploy from a branch"**
4. Branch: **main** | Folder: **/ (root)**
5. Clic en **Save**
6. En ~2 minutos tu URL estará disponible:
   **`https://TU_USUARIO.github.io/dashboard-faltantes`**

---

### 5️⃣  Conectar Netlify para mejor URL (opcional)
1. Ve a **https://netlify.com** → Sign up con tu cuenta GitHub
2. **"Add new site" → "Import an existing project" → GitHub**
3. Selecciona `dashboard-faltantes`
4. Build command: (vacío) | Publish directory: `.`
5. **"Deploy site"**
6. En Site settings puedes cambiar el nombre a algo como:
   `dsanver-faltantes.netlify.app`

---

## USO DIARIO — Actualizar los datos

### Cada vez que quieras actualizar el dashboard:

1. Ve a tu repositorio en GitHub
2. Entra a la carpeta **`data/`**
3. Clic en **"Add file" → "Upload files"**
4. **Arrastra** el archivo `Historico_de_faltantes.xlsx` actualizado
5. Clic en **"Commit changes"**

✅ **Listo.** GitHub procesa el Excel automáticamente en ~2 minutos.
   El dashboard en tu URL pública se actualiza solo.

---

## ¿Cómo saber que ya se actualizó?

En tu repositorio → pestaña **Actions**

Verás el proceso corriendo con una bolita amarilla ⏳  
Cuando termina, la bolita se vuelve verde ✅

Si hay un error, aparece en rojo ❌ — puedes reenviar el mensaje de error a Claude para ayuda.

---

## Estructura final del repositorio

```
dashboard-faltantes/
├── index.html                          ← El dashboard (nunca lo toques)
├── data.json                           ← Generado automáticamente
├── data/
│   └── Historico_de_faltantes.xlsx    ← Aquí subes el Excel actualizado
├── scripts/
│   └── procesar_datos.py              ← Corre en la nube (no lo toques)
└── .github/
    └── workflows/
        └── actualizar.yml             ← Automatización (no lo toques)
```

---

## Preguntas frecuentes

**¿Si cambio de computadora?**
No importa — todo está en la nube. Entras a GitHub desde cualquier navegador.

**¿Si olvido la contraseña de GitHub?**
GitHub tiene recuperación por correo electrónico.

**¿La URL cambia alguna vez?**
No. Una vez configurada es permanente.

**¿Cuánto tarda en actualizarse?**
Generalmente 1-3 minutos después de subir el Excel.

**¿Tiene costo?**
No. GitHub y Netlify son gratuitos para este uso.

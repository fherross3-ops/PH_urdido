// netlify/functions/agregar-comentario.js
// Recibe un comentario del dashboard y lo añade a data/comentarios.csv en GitHub

export default async (req) => {
  // Solo POST
  if (req.method !== 'POST') {
    return json({ error: 'Método no permitido' }, 405);
  }

  // Leer body
  let body;
  try {
    body = await req.json();
  } catch (e) {
    return json({ error: 'JSON inválido' }, 400);
  }

  const { fecha, nombre, categoria, maquina, comentario } = body;

  // Validación
  if (!fecha || !comentario || comentario.trim().length === 0) {
    return json({ error: 'Faltan fecha o comentario' }, 400);
  }

  // Sanitizar (evitar inyección en CSV y XSS)
  const limpiar = (s) => String(s || '')
      .replace(/"/g, '""')          // escapar comillas dobles
      .replace(/[\r\n]+/g, ' ')     // quitar saltos de línea
      .trim()
      .slice(0, 500);               // limitar longitud

  const nombreLimpio    = limpiar(nombre)    || 'Anónimo';
  const categoriaLimpia = limpiar(categoria) || 'General';
  const maquinaLimpia   = limpiar(maquina)   || '';
  const comentarioLimpio = limpiar(comentario);
  const timestamp = new Date().toISOString();

  // Config GitHub
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return json({ error: 'Token de GitHub no configurado en Netlify' }, 500);
  }

  const owner = 'fherross3-ops';
  const repo  = 'PH_urdido';
  const ruta  = 'data/comentarios.csv';
  const apiBase = `https://api.github.com/repos/${owner}/${repo}/contents/${ruta}`;

  const headers = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'urdido-dashboard'
  };

  try {
    // 1. Leer el archivo actual (para obtener el SHA y el contenido)
    const getResp = await fetch(apiBase, { headers });
    if (!getResp.ok) {
      const err = await getResp.json();
      return json({ error: 'No se pudo leer el CSV: ' + (err.message || getResp.status) }, 500);
    }
    const getData = await getResp.json();

    // GitHub devuelve el contenido en base64 (puede tener saltos de línea)
    const contenidoActual = Buffer.from(getData.content, 'base64').toString('utf-8');
    const lineas = contenidoActual.split('\n').filter(l => l.trim() !== '');

    // 2. Calcular el próximo ID
    let ultimoId = 0;
    for (let i = 1; i < lineas.length; i++) {
      const cols = parseCSVLine(lineas[i]);
      const id = parseInt(cols[0]);
      if (!isNaN(id) && id > ultimoId) ultimoId = id;
    }
    const nuevoId = ultimoId + 1;

    // 3. Construir la nueva fila
    const escaparCSV = (s) => {
      const str = String(s ?? '');
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return '"' + str.replace(/"/g, '""') + '"';
      }
      return str;
    };
    const nuevaFila = [
      nuevoId,
      fecha,
      timestamp,
      escaparCSV(nombreLimpio),
      escaparCSV(categoriaLimpia),
      escaparCSV(maquinaLimpia),
      escaparCSV(comentarioLimpio)
    ].join(',');

    const contenidoNuevo = contenidoActual.trimEnd() + '\n' + nuevaFila + '\n';

    // 4. Hacer commit en GitHub
    const putResp = await fetch(apiBase, {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: `Comentario #${nuevoId} - ${fecha} - ${categoriaLimpia}`,
        content: Buffer.from(contenidoNuevo, 'utf-8').toString('base64'),
        sha: getData.sha
      })
    });

    if (!putResp.ok) {
      const err = await putResp.json();
      return json({ error: 'No se pudo guardar: ' + (err.message || putResp.status) }, 500);
    }

    return json({
      ok: true,
      comentario: {
        id: nuevoId,
        fecha,
        timestamp,
        nombre: nombreLimpio,
        categoria: categoriaLimpia,
        maquina: maquinaLimpia,
        comentario: comentarioLimpio
      }
    }, 201);

  } catch (err) {
    return json({ error: 'Error interno: ' + err.message }, 500);
  }
};

// Helper para respuesta JSON
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
  });
}

// Parser simple de línea CSV (para calcular el último ID)
function parseCSVLine(line) {
  const values = [];
  let current = '';
  let insideQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (insideQuotes && line[i + 1] === '"') { current += '"'; i++; }
      else insideQuotes = !insideQuotes;
    } else if (ch === ',' && !insideQuotes) {
      values.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  values.push(current);
  return values;
}

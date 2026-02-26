#!/usr/bin/env node

/**
 * Script de inicialización del mock-server
 * Copia db_example.json a db.json si db.json no existe
 */

const fs = require('fs');
const path = require('path');

const dbExamplePath = path.join(__dirname, 'db_example.json');
const dbPath = path.join(__dirname, 'db.json');

// Verificar si db.json existe
if (!fs.existsSync(dbPath)) {
  console.log('📋 db.json no existe. Inicializando desde db_example.json...');
  
  // Verificar que db_example.json existe
  if (!fs.existsSync(dbExamplePath)) {
    console.error('❌ Error: db_example.json no encontrado');
    process.exit(1);
  }
  
  // Copiar db_example.json a db.json
  try {
    fs.copyFileSync(dbExamplePath, dbPath);
    console.log('✅ db.json inicializado correctamente desde db_example.json');
  } catch (error) {
    console.error('❌ Error al copiar db_example.json:', error.message);
    process.exit(1);
  }
} else {
  console.log('✓ db.json ya existe, no se requiere inicialización');
}


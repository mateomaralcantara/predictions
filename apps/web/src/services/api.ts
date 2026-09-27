// services/api.ts

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Ajusta si tu backend cambia de puerto

// 🚀 Instancia de Axios para reusar configuración
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 🔥 Función de manejo de errores
const manejarError = (error: unknown, nombreFuncion: string) => {
  console.error(`❌ Error en ${nombreFuncion}:`, error);
  throw error;
};

// ✅ Consultar explicación de un número
export const getExplicacionNumero = async (numero: number) => {
  try {
    const response = await api.get(`/explicacion-numero/${numero}`);
    return response.data;
  } catch (error) {
    manejarError(error, "getExplicacionNumero");
  }
};

// ✅ Consultar chat general
export const chatConIA = async (prompt: string) => {
  try {
    const response = await api.post('/chat', { prompt });
    return response.data;
  } catch (error) {
    manejarError(error, "chatConIA");
  }
};

// ✅ Insertar resultado loto
interface LotoData {
  numero: number;
  fecha: string;
  premio: number;
}

export const insertarResultadoLoto = async (data: LotoData) => {
  try {
    const response = await api.post('/insertar-loto/', data);
    return response.data;
  } catch (error) {
    manejarError(error, "insertarResultadoLoto");
  }
};

// ✅ Crear orden de pago PayPal
export const crearOrdenPaypal = async (amount: string, currency = "USD") => {
  try {
    const response = await api.post('/paypal/create-order', { amount, currency });
    return response.data;
  } catch (error) {
    manejarError(error, "crearOrdenPaypal");
  }
};

// ✅ Capturar orden de pago PayPal
export const capturarOrdenPaypal = async (orderId: string) => {
  try {
    const response = await api.post(`/paypal/capture-order/${orderId}`);
    return response.data;
  } catch (error) {
    manejarError(error, "capturarOrdenPaypal");
  }
};

// ✅ Consultar resultados tradicionales
export const getResultadosTradicionales = async () => {
  try {
    const response = await api.get('/resultados');
    return response.data;
  } catch (error) {
    manejarError(error, "getResultadosTradicionales");
  }
};

// ✅ Consultar top 10 números más salidores
export const getTopNumeros = async () => {
  try {
    const response = await api.get('/top-numeros/');
    return response.data;
  } catch (error) {
    manejarError(error, "getTopNumeros");
  }
};

// ✅ Nuevo endpoint para preguntar al sistema y consultar la base
export const preguntarAlSistema = async (pregunta: string) => {
  try {
    const response = await api.post('/preguntar/', { pregunta });
    return response.data;
  } catch (error) {
    manejarError(error, "preguntarAlSistema");
  }
};

// ✅ Nuevo endpoint para preguntar al sistema y consultar la base de datos
// (Eliminado porque ya existe una implementación de preguntarAlSistema)

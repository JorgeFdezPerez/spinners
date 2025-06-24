#Variables con dirección de conexión
NODES_ESTADO = {
    "Estado Bases": "ns=1;s=ME_BASES_EstadoActual",
    "Estado Spinners": "ns=1;s=ME_SPINNERS_EstadoActual",
    "Estado Transporte": "ns=1;s=ME_TRANSPORTE_EstadoActual",
}

SERVICIOS = {
    "Servicio Bases": ("BASES", "ns=1;s=ME_BASES_ServicioActual"),
    "Servicio Spinners": ("SPINNERS", "ns=1;s=ME_SPINNERS_ServicioActual"),
    "Servicio Transporte": ("TRANSPORTE", "ns=1;s=ME_TRANSPORTE_ServicioActual"),
}

POS = {
    "Posición Transporte Actual": "ns=1;s=ME_TRANSPORTE_PosActual",
    "Posición Transporte Objetivo": "ns=1;s=ME_TRANSPORTE_PosObj",
}

DETECT_BASES = {
    "A0":"ns=1;s=ME_BASES_A0",
    "A1":"ns=1;s=ME_BASES_A1",
    "Empty":"ns=1;s=ME_BASES_Empty",
    "Base":"ns=1;s=ME_BASES_Base",
    "Aminus":"ns=1;s=ME_BASES_Aminus"
}

DETECT_SPINNERS = {
    "A0":"ns=1;s=ME_SPINNERS_A0",
    "A1":"ns=1;s=ME_SPINNERS_A1",
    "Base":"ns=1;s=ME_SPINNERS_Base",
    "Transporte Preparado Para Recoger Spinner":"ns=1;s=ME_SPINNERS_TransportePreparadoParaRecogerSpinner",
    "Aminus":"ns=1;s=ME_SPINNERS_Aminus",
    "Aplus":"ns=1;s=ME_SPINNERS_Aplus",
    "Spinners Preparado Para Dispensar":"ns=1;s=ME_SPINNERS_SpinnersPreparadoParaDispensar",
    "Spinners Acabado De Expulsar Base":"ns=1;s=ME_SPINNERS_SpinnersAcabadoDeExpulsarBase"
}

DETECT_TRANSPORTE = {
    "B0":"ns=1;s=ME_TRANSPORTE_B0",
    "B1":"ns=1;s=ME_TRANSPORTE_B1",
    "C0":"ns=1;s=ME_TRANSPORTE_C0",
    "C1":"ns=1;s=ME_TRANSPORTE_C1",
    "BPlus":"ns=1;s=ME_TRANSPORTE_BPlus",
    "BMinus":"ns=1;s=ME_TRANSPORTE_BMinus",
    "CPlus":"ns=1;s=ME_TRANSPORTE_CPlus",
    "CMinus":"ns=1;s=ME_TRANSPORTE_CMinus",
    "Busy":"ns=1;s=ME_TRANSPORTE_Busy",
    "INP":"ns=1;s=ME_TRANSPORTE_INP",
    "Hold":"ns=1;s=ME_TRANSPORTE_Hold",
    "Preparado Para Recoger Spinner":"ns=1;s=ME_TRANSPORTE_PreparadoParaRecogerSpinner",
}

ALARM_BASES = {
    "Alarmas dos detectados":"ns=1;s=ME_BASES_Alarmas_dos_detect",
    "Alarma base":"ns=1;s=ME_BASES_Alarma_base",
    "Alarma retroceso":"ns=1;s=ME_BASES_Alarma_retroceso",
    "Alarma avance":"ns=1;s=ME_BASES_Alarma_avance"
}

ALARM_SPINNERS = {
    "Error Sensores A Simultaneos":"ns=1;s=ME_SPINNERS_ErrorSensoresASimultaneos",
    "Error A0 No Activo":"ns=1;s=ME_SPINNERS_ErrorA0NoActivo",
    "Error A1 No Activo":"ns=1;s=ME_SPINNERS_ErrorA1NoActivo",
}

ALARM_TRANSPORTE = {
    "Error Sensores B Simultaneos":"ns=1;s=ME_TRANSPORTE_ErrorSensoresBSimultaneos",
    "Error Sensores C Simultaneos":"ns=1;s=ME_TRANSPORTE_ErrorSensoresCSimultaneos",
    "Error B0 No Activo Transporte":"ns=1;s=ME_TRANSPORTE_ErrorB0NoActivoTransporte",
    "Error B1 No Activo Transporte":"ns=1;s=ME_TRANSPORTE_ErrorB1NoActivoTransporte",
    "Error C0 No Activo Transporte":"ns=1;s=ME_TRANSPORTE_ErrorC0NoActivoTransporte",
    "Error C1 No Activo Transporte":"ns=1;s=ME_TRANSPORTE_ErrorC1NoActivoTransporte",
    "Error Mover Con Pinza Extendida":"ns=1;s=ME_TRANSPORTE_ErrorMoverConPinzaExtendida",
    "Error Coger Base Con Pinza Ocupada":"ns=1;s=ME_TRANSPORTE_ErrorCogerBaseConPinzaOcupada",
    "Error Driver No Responde":"ns=1;s=ME_TRANSPORTE_ErrorDriverNoResponde",
    "Error Coger Spinner Sin Base":"ns=1;s=ME_TRANSPORTE_ErrorCogerSpinnerSinBase"
}
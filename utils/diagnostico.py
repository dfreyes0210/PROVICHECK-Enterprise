def generar_diagnostico_sesion(estado_sesion, total, cumplen, no_cumplen, no_evaluados):
    if total == 0:
        return "No se registraron puntos de verificación."

    if estado_sesion == "Conforme":
        return (
            "La verificación fue conforme. Todos los puntos evaluados se encuentran "
            "dentro de los límites establecidos. Se recomienda continuar con la "
            "frecuencia de verificación definida."
        )

    if estado_sesion == "No conforme":
        return (
            f"La verificación fue no conforme. Se detectaron {no_cumplen} punto(s) "
            "fuera de los límites establecidos. Se recomienda revisar el equipo, "
            "evaluar su uso y registrar la acción correspondiente en la bitácora."
        )

    if estado_sesion == "Completa con puntos no evaluados":
        return (
            f"La verificación se considera realizada con {no_evaluados} punto(s) "
            "no evaluado(s) y debidamente justificado(s). Estos puntos no deben "
            "incorporarse a las tendencias ni a la estadística de resultados. "
            "La causa queda documentada para trazabilidad."
        )

    if estado_sesion == "Incompleta":
        return (
            f"La verificación está incompleta. Existen {no_evaluados} punto(s) "
            "sin evaluación válida o sin justificación suficiente. La sesión no "
            "debe cerrarse hasta documentar correctamente la causa."
        )

    return "Resultado de verificación pendiente de análisis."
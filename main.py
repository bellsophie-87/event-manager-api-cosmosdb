from fastapi import FastAPI, HTTPException, Query, Path
from typing import List, Optional
from database import container
from models import Evento, Participante
from azure.cosmos import exceptions
from datetime import datetime

app = FastAPI(title = 'API' )

@app.get("/")
def home():
    return "Hola Mundo"

# Crear evento
@app.post("/events/", response_model  = Evento, status_code = 201)
def create_event(event: Evento):
    try:
        container.create_item(body = event.dict())
        return event
    except exceptions.CosmosResourceExistsError:
        raise HTTPException(status_code = 400, detail = "El evento con este ID ya existe")
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code = 400, detail = str(e))


# Obtener evento por id
@app.get("/events/{event_id}", response_model  = Evento, status_code = 201)
def get_event(event_id: str = Path(...,description = "ID del evento a recuperar")):
    try:
        evento = container.read_item(item = event_id, partition_key = event_id)
        return evento
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code = 404, detail = "Evento no encontrado")
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code = 400, detail = str(e))

# Listar eventos
@app.get("/events/", response_model  = List[Evento])
def list_event():   
    query = "select * from c where 1=1"
    items = list(container.query_items(query = query, enable_cross_partition_query = True))
    return items

# Actualizar evento por id
@app.put("/events/{event_id}", response_model  = Evento, status_code = 201)
def update_event(event_id: str , updated_event: Evento):
    existing_event = container.read_item(item = event_id, partition_key = event_id)
    existing_event.update(updated_event.dict(exclude_unset = True))

    if existing_event['capacity'] < len(existing_event['participantes']):
        raise HTTPException(status_code = 404, detail = "no se pudo insertar")

    container.replave_item(item = event_id, body = existing_event)

    return existing_event


# Eliminar evento por id
@app.delete("/events/{event_id}", status_code = 204)
def delete_event(event_id: str):
    try:
        container.delete_item(item = event_id, partition_key = event_id)
        return
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code = 404, detail = "Evento no encontrado")
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code = 400, detail = str(e))


# Endpoints de los participantes

# Eliminar evento por id
@app.post("/events/{event_id}/participantes/", response_model = Participante, status_code = 201)
def add_participante(event_id: str, participante: Participante):
    # validar si el participante ya existe

    try:
        
        event = container.read_item(item=event_id, partition_key=event_id)

        if len(event['participantes']) >= event['capacity'] :
            raise HTTPException(status_code=400, detail='Capacidad maxima del evento alcanzado')

        if any( p['id'] == participante.id for p in event['participantes'] ):
            raise HTTPException(status_code=400, detail='El partipante con este Id ya esta inscrito')

        event['participantes'].append(participante.dict())

        container.replace_item(item=event_id, body=event)

        return participante
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail='Evento no encotrado')
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=400, detail=str(e)) 


# Listar eventos
@app.get("/events/{event_id}/participants/{participant_id}")
def get_participante(event_id: str, participant_id: str):

    try:
        event = container.read_item(item=event_id, partition_key=event_id)
        
        participant = next((p for p in event['participantes'] if p['id'] == participant_id), None)

        if participant:
            return participant
        else:
            raise HTTPException(status_code=404, detail='Participante no encotrado')
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail='Evento no encotrado')
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/events/{event_id}/participants/", response_model = List[Participante])
def list_participantes(event_id: str):
    try:
        event = container.read_item(item=event_id, partition_key=event_id)

        participantes = event.get('participantes', [])

        return participantes
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail='Evento no encotrado')
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Actualizar participante por id
@app.put("/events/{event_id}/participantes/{participante_id}", response_model  = Participante, status_code = 201)
def update_participante(event_id: str , participante_id: str, updated_participante: Participante):
    try:
        event = container.read_item(item=event_id, partition_key=event_id)
        participante = next((p for p in event['participantes'] if p['id'] == participante_id), None)

        if not participante:
            raise HTTPException(status_code=404, detail='Participante no encotrado')
            
        participante.update(updated_participante.dict(exclude_unset = True))

        #lista_nueva = []
        #for p in event['participantes']:
        #    if p['id'] != participante_id:
        #       lista_nueva.append(p)
        #    else:
        #        lista_nueva.append(participant)

        event['participantes'] = [p if p['id'] != participante_id else participante for p in event['participantes']]

        container.replace_item(item = event_id, body = event)
        return participante

    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail='Participante no encotrado')
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Eliminar participapnte por id
@app.delete("/events/{event_id}/participantes/{participante_id}", status_code = 204)
def delete_event(event_id: str,participante_id: str):
    try:
        event = container.read_item(item=event_id, partition_key=event_id)
        participante = next((p for p in event['participantes'] if p['id'] == participante_id), None)

        if not participante:
            raise HTTPException(status_code=404, detail='Participante no encotrado')
          
        event['participantes'] = [p for p in event['participantes'] if p['id'] != participante_id]
        container.replace_item(item = event_id, body = event)
        return
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code = 404, detail = "Evento no encontrado")
    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code = 400, detail = str(e))

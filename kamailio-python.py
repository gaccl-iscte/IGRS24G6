import KSR as KSR
import json
import os
import re

class StateDatabase:
    def __init__(self, filename="state_db.json"):
        self.filename = filename
        self.db = {}
        self.load_from_file()

    def set_state(self, key, value):
        self.db[key] = value
        self.save_to_file()

    def get_state(self, key):
        return self.db.get(key, None)

    def remove_state(self, key):
        if key in self.db:
            del self.db[key]
            self.save_to_file()

    def save_to_file(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.db, f)
        except Exception as e:
            KSR.err(f"Erro ao salvar o estado no arquivo: {e}\n")

    def load_from_file(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.db = json.load(f)
            except Exception as e:
                KSR.err(f"Erro ao carregar o estado do arquivo: {e}\n")

state_db = StateDatabase()

def mod_init():
    KSR.info("===== from Python mod init\n")
    return PBX2Service()

class PBX2Service:
    def __init__(self):
        KSR.info('===== kamailio.__init__\n')
        self.total_calls = 0
        self.total_conferences = 0
        self.total_forwarded_calls = 0

    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0

    def ksr_request_route(self, msg):
        if msg.Method == "REGISTER":
            return self.handle_register(msg)
        elif msg.Method == "INVITE":
            return self.handle_invite(msg)
        elif msg.Method == "BYE":
            return self.handle_bye(msg)
        elif msg.Method == "MESSAGE":
            return self.handle_message(msg)
        elif msg.Method == "ACK":
            return self.handle_ack(msg)
        elif msg.Method == "CANCEL":
            return self.handle_cancel(msg)
        else:
            KSR.info(f"Metodo não suportado: {msg.Method}\n")
            return 1
    
    def handle_register(self, msg):
        
        user = KSR.pv.get("$tu")
        contact = KSR.hdr.get("Contact")
        domain = KSR.pv.get("$td")
        expires = KSR.pv.get("$hdr(Expires)")
        
        if (domain != "acme.pt"):
            KSR.info("Domínio Incorreto")
            KSR.sl.send_reply(403, "Forbidden")
            return 1
        
        if (expires == 0 and int(expires)) and KSR.registrar.save("location", 1):
            if state_db.get_state(user):
                state_db.remove_state(user)
                KSR.info(f"User - {user} removed\n")
                KSR.sl.send_reply(200, "OK")
        elif (expires == 0 and int(expires)) and KSR.registrar.save("location", 0):
            KSR.sl.send_reply(404, "Not Found")
            return 1
        
        state_db.set_state(user, {"contact": contact, "status": "available", "in_conference": "false"})
        KSR.registrar.save("location", 1)
        KSR.info(f"User {user} registado com o contato {contact}\n")
        KSR.sl.send_reply(200, "OK")
        return 1
    
    def handle_message(self, msg):
        origin = KSR.pv.get("$fu")               
        destination = KSR.pv.get("$ru")
        sip_body = KSR.pv.get("$rb")
        
        if(destination == "sip:validar@acme.pt" and sip_body == "0000"):
            KSR.info("PIN Válido")
            KSR.sl.send_reply(200, "OK")
        else:
            KSR.info("Pin Inválido")
            KSR.sl.send_reply(403, "Forbidden")
        
        if (origin == "sip:gestor@acme.pt" and sip_body == "Report"):
            self.metrics(msg)        
        return 1
                
    
    def handle_invite(self, msg):        
        origin = KSR.pv.get("$fu")
        origin_domain = KSR.pv.get("$fd")
        destination = KSR.pv.get("$ru")
        destination_json = KSR.pv.get("$tu")
        origin_state = state_db.get_state(origin)
        destination_state = state_db.get_state(destination_json)
        
        if(origin_domain != "acme.pt"):
            KSR.sl.send_reply(403, "Forbidden")
            
        if(destination == "sip:conferencia@acme.pt"):
            if origin_state:
                state_db.set_state(origin, {"contact": origin_state["contact"], "status": "busy", "in_conference": "true"})
                KSR.info(f"Estado de {origin} atualizado para 'busy' e 'in_conference'\n")
            KSR.pv.sets("$ru", "sip:conferencia@127.0.0.1:5090")
            KSR.tm.t_relay()
            self.total_forwarded_calls += 1
            return 1
        
        if(destination_state["status"] == "busy" and destination_state["in_conference"] == "true"):
                KSR.pv.sets("$ru", "sip:inconference@127.0.0.1:5080")
                KSR.info(f"Reencaminhado para inconference")
                KSR.forward()
                KSR.tm.t_relay()
                self.total_conferences += 1
                self.total_forwarded_calls += 1
                return 1
        elif (destination_state["status"] == "busy" and destination_state["in_conference"] == "false"):
                KSR.pv.sets("$ru", "sip:busyann@127.0.0.1:5080")
                KSR.forward()
                KSR.info(f"Reencaminhado para busyann")
                KSR.tm.t_relay()
                self.total_forwarded_calls += 1
                return 1
                
        if KSR.registrar.lookup("location") == 0:
            KSR.sl.send_reply(404, "Not Found")
            return 1
        
        state_db.set_state(origin, {"contact": origin_state["contact"], "status": "busy", "in_conference": "false"})
        KSR.info(f"Estado da origem atualizado para 'busy': {origin}\n")
        state_db.set_state(destination, {"contact": destination_state["contact"], "status": "busy", "in_conference": "false"})
        KSR.info(f"Estado do destino atualizado para 'busy': {destination}\n")
        
        contact = destination_state["contact"]
        match = re.search(r"<(sip:[^>]+)>", contact)
        if match:
            contact = match.group(1)
        else:
            contact = contact.split(";")[0]

        KSR.pv.sets("$ru", contact)
        KSR.info(f"Reencaminhando INVITE para {contact}\n")
        try:
            if not KSR.tm.t_relay():
                KSR.err(f"Falha ao reencaminhar a chamada de {origin} para {destination}\n")
        except Exception as e:
            KSR.err(f"Erro durante reencaminhamento: {e}\n")
            
        self.total_calls += 1
        return 1
    
    def handle_bye(self, msg):        
        origin = KSR.pv.get("$fu")
        destination = KSR.pv.get("$ru")
        destination_json = KSR.pv.get("$tu")
        origin_state = state_db.get_state(origin)
        destination_state = state_db.get_state(destination_json)

        KSR.info(f"BYE recebido: origem {origin}, destino {destination}\n")

        if origin_state:
            state_db.set_state(origin, {"contact": origin_state["contact"], "status": "available", "in_conference": "false"})
            KSR.info(f"Estado atualizado para 'available' para origem: {origin}\n")
        else:
            KSR.err(f"Estado não encontrado para origem: {origin}\n")

        if destination_state:
            state_db.set_state(destination, {"contact": destination_state["contact"], "status": "available", "in_conference": "false"})
            KSR.info(f"Estado atualizado para 'available' para o destino: {destination}\n")
        else:
            KSR.err(f"Estado não encontrado para o destino: {destination}\n")
            
        KSR.rr.loose_route()
        KSR.tm.t_relay()
        return 1
    
    def handle_ack(self, msg):
        KSR.info("ACK R-URI: " + KSR.pv.get("$ru") + "\n")
        KSR.rr.loose_route()
        KSR.tm.t_relay()
        return 1        
    
    def handle_cancel(self, msg):
        KSR.info("CANCEL R-URI: " + KSR.pv.get("$ru") + "\n")
        KSR.registrar.lookup("location")
        KSR.tm.t_relay()
        return 1
    
    def metrics(self, msg):
        metrics = (
        f"total_calls: {self.total_calls}\n"
        f"total_conferences: {self.total_conferences}\n"
        f"total_forwarded_calls: {self.total_forwarded_calls}\n"
        )
        
        destination = KSR.pv.get("$fu")        
        KSR.msg.send(destination, metrics)
        
    def ksr_reply_route(self, msg):
        """Rota para lidar com respostas"""
        KSR.info("Resposta recebida\n")
        return 1

    def ksr_onsend_route(self, msg):
        """Rota chamada antes do envio de mensagens"""
        KSR.info("Mensagem enviada\n")
        return 1
        
        
    

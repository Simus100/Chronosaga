# chronosaga_app.py  –  UI refined (pages & larger font)
"""
ChronoSaga • text‑based RPG (Gradio 5.29).  
Novità UI:
* Font base 20 px per massima leggibilità.
* Ogni **step del wizard** è una pagina: quando prosegui, il passo precedente
  scompare (non solo il bottone), rendendo l’esperienza lineare.
* Layout identico al codice precedente, nessuna logica di gioco toccata.
"""

import os, json, random
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

import gradio as gr
from gradio.themes import Soft
if not hasattr(gr, "Box"):
    gr.Box = getattr(gr, "Group", gr.Column)
from openai import OpenAI

MODEL_NAME = "gpt-3.5-turbo"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

THEME = Soft()
CUSTOM_CSS = """
html,body{font-family:'Inter',sans-serif;font-size:20px;line-height:1.65;}
.gr-button{padding:0.8rem 1.8rem!important;border-radius:10px!important;font-size:1.1rem!important}
.gr-input,.gr-textbox,.gr-dropdown{border-radius:8px!important}
.gr-markdown{font-size:1.15rem!important;line-height:1.65}
/* risposta (output) – font più grande e spazio sopra/sotto */
.response{font-size:1.5rem!important;line-height:1.75;text-align:center;max-width:700px;margin:2rem auto;}
"""

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(MODULE_PATH,"ChronoSaga.txt")
try:
    with open(RULES_PATH,"r",encoding="utf-8") as fh:
        CHRONO_RULES = fh.read()
except FileNotFoundError:
    CHRONO_RULES = "(⚠️ Rules missing)"
AION_PROMPT = "Tu sei Aion – entità modulare …"
SYSTEM_PROMPT = AION_PROMPT+"\n\n"+CHRONO_RULES+"\nSei il narratore di ChronoSaga."

Stats = Dict[str,int]
@dataclass
class GameState:
    setting: Dict[str,str]=field(default_factory=dict)
    stats: Stats = field(default_factory=lambda:{k:0 for k in ["INT","FIS","DES","CHA","VOL"]})
    background:str=""; talent:str=""; name:str=""; description:str=""
    vit:int=5; en:int=0; level:int=1; karma:int=0; coins:int=0; items:List[str]=field(default_factory=list)
    zone:str="???"; time_of_day:str="Giorno"; weather:str="Sereno"
    dialogue: List[Dict[str,str]] = field(default_factory=list)
    def to_public_status(self):
        s=self.stats
        return (f"**👤 {self.name}**\n{self.description}\n\n"
                f"**📊** INT:{s['INT']} FIS:{s['FIS']} DES:{s['DES']} CHA:{s['CHA']} VOL:{s['VOL']}\n"
                f"**❤️** VIT:{self.vit} EN:{self.en} LIV:{self.level} KARMA:{self.karma}\n"
                f"**🌍** {self.zone} | {self.time_of_day} | {self.weather}\n"
                f"**💰** {self.coins} monete • Oggetti: {', '.join(self.items) or 'nessuno'}")

def roll_d20(): return random.randint(1,20)

def openai_narrate(gs:GameState,player:str,mech:Dict[str,Any]):
    payload={"game_state":asdict(gs),"player_input":player,"mechanics":mech}
    msgs=[{"role":"system","content":SYSTEM_PROMPT},*gs.dialogue[-10:],{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]
    rsp=client.chat.completions.create(model=MODEL_NAME,messages=msgs,temperature=0.7,max_tokens=1200)
    narr=rsp.choices[0].message.content.strip()
    gs.dialogue+=[{"role":"user","content":player},{"role":"assistant","content":narr}]
    return narr

def process_player_action(gs:GameState,act:str):
    mech={}
    low=act.lower().strip()
    if low.startswith("tira "):
        try:
            _,stat,thr=act.split(); stat=stat.upper(); thr=int(thr)
            r=roll_d20(); tot=r+gs.stats.get(stat,0)
            mech["test"]={"stat":stat,"thr":thr,"roll":r,"mod":gs.stats.get(stat,0),"total":tot,"outcome":"Successo" if tot>=thr else "Fallimento"}
        except ValueError:
            return "Formato corretto: tira DES 12"
    elif low=="mostra parametri":
        return gs.to_public_status()
    narr=openai_narrate(gs,act,mech)
    return narr+"\n\n_Comandi_: mostra parametri • esplora • commercia • salva"

def build_ui():
    with gr.Blocks(theme=THEME,css=CUSTOM_CSS,title="ChronoSaga") as ui:
        gs_state=gr.State(GameState())

        # STEP 1
        with gr.Box() as step1_box:
            gr.Markdown("## 🟢 Step 1 – Ambientazione")
            genre=gr.Dropdown(["Fantasy","Sci‑Fi","Horror","Cyberpunk","Altro"],label="Genere")
            tone=gr.Dropdown(["Epico","Cupo","Ironico","Drammatico","Libero"],label="Tono")
            play=gr.Dropdown(["Combattimento","Investigazione","Esplorazione","Diplomazia","Sopravvivenza"],label="Stile")
            diff=gr.Dropdown(["Narrativo","Bilanciato","Tattico"],label="Difficoltà")
            moral=gr.Dropdown(["Alta","Media","Bassa"],label="Scelte morali")
            karma=gr.Radio(["Sì","No"],label="Abilita Karma?",value="Sì")
            next1=gr.Button("Avanti ➡️")

        # STEP 2
        with gr.Box(visible=False) as step2_box:
            gr.Markdown("## 🟡 Step 2 – Distribuisci 11 punti")
            pts=gr.Number(value=11,label="Punti rimanenti",interactive=False)
            sliders={k:gr.Slider(0,5,0,label=k) for k in ["INT","FIS","DES","CHA","VOL"]}
            next2=gr.Button("Avanti ➡️")

        # STEP 3
        with gr.Box(visible=False) as step3_box:
            gr.Markdown("## 🔵 Step 3 – Background & Talento")
            background=gr.Textbox(lines=2,label="Background unico")
            talent=gr.Textbox(lines=1,label="Talento base")
            next3=gr.Button("Avanti ➡️")

        # STEP 4
        with gr.Box(visible=False) as step4_box:
            gr.Markdown("## 🟣 Step 4 – Identità giocatore")
            char_name=gr.Textbox(label="Nome personaggio")
            char_desc=gr.Textbox(lines=2,label="Descrizione evocativa")
            finish=gr.Button("✨ Inizia l’avventura")

        # GAME
        with gr.Box(visible=False) as game_box:
            status=gr.Markdown()
            txt=gr.Textbox(placeholder="es. *esplora rovine*",label="Azione / comando")
            send=gr.Button("Invia")
            output=gr.Markdown(elem_classes="response")

        # CALL‑BACKS
        def to_step2(g,t,p,m,k,d,gs:GameState):
            gs.setting={"Genere":g,"Tono":t,"Stile":p,"Morale":m,"Karma":k,"Diff":d}
            return {step1_box:gr.update(visible=False), step2_box:gr.update(visible=True)}
        next1.click(to_step2,inputs=[genre,tone,play,moral,karma,diff,gs_state],outputs=[step1_box,step2_box])

        slider_list=list(sliders.values())
        for sl in slider_list:
            sl.change(lambda *v: 11-sum(v),inputs=slider_list,outputs=pts)

        def to_step3(gs:GameState,*vals):
            if sum(vals)!=11: raise gr.Error("Devi usare tutti gli 11 punti.")
            gs.stats.update({k:v for k,v in zip(sliders.keys(),vals)})
            return {step2_box:gr.update(visible=False), step3_box:gr.update(visible=True)}
        next2.click(to_step3,inputs=[gs_state,*slider_list],outputs=[step2_box,step3_box])

        def to_step4(bg,tl,gs:GameState):
            gs.background, gs.talent = bg, tl
            return {step3_box:gr.update(visible=False), step4_box:gr.update(visible=True)}
        next3.click(to_step4,inputs=[background,talent,gs_state],outputs=[step3_box,step4_box])

        def start(nm, ds, gs: GameState):
            gs.name, gs.description = nm, ds
            intro = openai_narrate(gs, "__START__", {})
            return {
                step4_box: gr.update(visible=False),
                game_box: gr.update(visible=True),
                status: gr.update(value=gs.to_public_status()),
                output: gr.update(value=intro),
            }

        finish.click(
            start,
            inputs=[char_name, char_desc, gs_state],
            outputs=[step4_box, game_box, status, output],
        )

        # ─── Loop di gioco ───
        def turn(gs: GameState, act: str):
            reply = process_player_action(gs, act)
            return gs.to_public_status(), reply, ""

        send.click(turn, inputs=[gs_state, txt], outputs=[status, output, txt])

    return ui


# ────────── AVVIO ──────────
if __name__ == "__main__":
    build_ui().launch()

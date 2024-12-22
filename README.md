# IGRS24G6
Repositório para o projeto - Serviço "PBX2.0"
### Members
```
98616 - Bernardo Assunção - METI-PL-A1 - Bernardo_Assuncao@iscte-iul.pt
98931 - Filipe Vasconcelos - METI-PL-A1 - Filipe_Vasconcelos@iscte-iul.pt
98624 - Gonçalo Lobato - METI-PL-A1 - Goncalo_Lobato@iscte-iul.pt
99435 - Nuno Teixeira - METI-PL-A1 - Nuno_Oliveira_Teixiera@iscte-iul.pt
```
### Commands:
```
sudo kamailio -f kamailio-python.cfg -E -D 2

twinkle –f Alice --sip-port 5555 --rtp-port 7777 --force &

twinkle –f Trudy --sip-port 7777 --rtp-port 9999 --force &

twinkle –f Bob --sip-port 6666 --rtp-port 8888 --force &

sems -f semsconf.cfg -E -D 2

sems -f semsannounce.cfg -E -D 2
```
### Trello:
```
https://trello.com/w/igrs24g6
```

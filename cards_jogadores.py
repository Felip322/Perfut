# add_cards.py
from app import app, db, Card
import json

cards_data = [
    # Jogador 1
    {
        "theme": "jogador_atividade",
        "title": "Jogador 1 - Neymar",
        "answer": "Neymar JR",
        "hints": [
            "Sou campeão olímpico.",
            "Ja fui campeão, e artilheiro de uma mesma edição de Champions League.",
            "Marquei o último gol de pênalti da Seleção Brasileira, em Copas do Mundo.",
            "Meu primeiro gol como profissional, foi marcado no Estádio do Pacaembu.",
            "Marquei gols em finais de Champions League, e Copa Libertadores da América, finais essas que fui campeão.",
            "Marquei gols em mundiais de clubes, vestindo a camisa de 2 clubes diferentes.",
            "Sou destro.",
            "Fiz minha estreia como jogador profissional, vestindo a camisa de número 18.",
            "Ja fui o vencedor, de uma edição do 'Premio Puskas'.",
            "Ja marquei 6 gols em partidas de Copa do Mundo"
        ],
        "difficulty": 3
    },
    # Jogador 2
    {
        "theme": "jogador_atividade",
        "title": "Jogador 2 - Fred",
        "answer": "Fred",
        "hints": [
            "Já formei dupla de ataque com Benzema.",
            "Sou o maior artilheiro de uma única edição de Copa do Brasil, feito alcançado em 2005.",
            "Sou 'Xará', do personagem mais famoso interpretado por Carlos Villagran.",
            "Sou autor do gol mais rápido da história do futebol mundial.",
            "Sou bicampeão Brasileiro, vestindo a camisa do mesmo time.",
            "Marquei o primeiro gol oficial da Seleção Brasileira, no novo Maracanã.",
            "Ja fui 3 vezes artilheiro do campeonato brasileiro.",
            "Nasci no dia 3 de outubro de 1983.",
            "Ja fui campeão vestindo a camisa da Seleção Brasileira.",
            "Participei duas Copas do Mundo, disputando 7 jogos, e marcando 2 gols."
        ],
        "difficulty": 3
    },
    # Jogador 3
    {
        "theme": "jogador_atividade",
        "title": "Jogador 3 - Messi",
        "answer": "Messi",
        "hints": [
            "Já marquei um gol com a mão.",
            "Sou tetra campeão da Champions League.",
            "O primeiro número de camisa em jogos oficiais que usei, foi o 30.",
            "Nunca vesti a camisa de um clube do meu país, profissionalmente.",
            "Vesti a camisa do mesmo time, por 16 anos.",
            "Sou campeão olímpico.",
            "Ja marquei gols, em duas finais diferentes, de Champions League.",
            "O Cirque du Soleil, tem um espetáculo com meu nome.",
            "Por clubes ja usei 3 números diferentes de camisa, de forma oficial.",
            "Ja marquei 6 gols em Copas do Mundo, porem nenhum em fase mata mata."
        ],
        "difficulty": 4
    },
    # Jogador 4
    {
        "theme": "jogador_atividade",
        "title": "Jogador 4 - Thiago Neves",
        "answer": "Thiago Neves",
        "hints": [
            "Sou tricampeão da Copa do Brasil, vestindo as camisas de Fluminense, e Cruzeiro.",
            "Sou canhoto.",
            "Fui revelado por um clube paranaense.",
            "Ja fui campeão vestindo as camisas da dupla Fla-Flu.",
            "Sou o único jogador da história, a marcar 3 gols em uma final de Copa Libertadores da América.",
            "Nasci no ano de 1985.",
            "Ja fui uma vez campeão brasileiro, título esse conquistado vestindo a camisa do Fluminense.",
            "Ja conquistei 3 estaduais diferentes.",
            "Ja vesti a camisa de 3 tricolores do Brasil.",
            "Sou medalhista olímpico."
        ],
        "difficulty": 3
    },
    # Jogador 5
    {
        "theme": "jogador_atividade",
        "title": "Jogador 5 - Ricardo Oliveira",
        "answer": "Ricardo Oliveira",
        "hints": [
            "Fui revelado pela Portuguesa.",
            "Tenho apelido religioso.",
            "Em 2017, foi respeitado um minuto de silêncio, devido a minha suposta morte, o curioso é que eu estava em campo.",
            "Vestindo a camisa do Santos fui bicampeão paulista, nos anos de 2015, e 2016.",
            "Conquistei uma vez o prêmio, 'Chuteira de Ouro' da Revista Placar, feito alcançado no ano de 2015.",
            "Ja fui campeão, duas vezes vestindo a camisa da seleção brasileira.",
            "Fui impedido de jogar uma final de Copa Libertadores da América, pois meu contato se encerrou no meio das finais.",
            "Sou destro.",
            "O primeiro título que conquistei, foi vestindo a camisa do Valencia.",
            "Fiz parte do elenco do Milan, campeão da Champions League, na temporada 2006/07."
        ],
        "difficulty": 3
    },
    # Jogador 6
    {
        "theme": "jogador_atividade",
        "title": "Jogador 6 - Toni Kroos",
        "answer": "Toni Kroos",
        "hints": [
            "Fui campeão mundial de clubes, e seleções, no mesmo ano.",
            "Sou tetra campeão da Champions League.",
            "Ja marquei gol contra a Seleção Brasileira, em Copa do Mundo.",
            "Marquei o último gol da Seleção Alemã, em Copas do Mundo.",
            "Fui revelado pelo Bayern de Munique.",
            "Visto a mesma camisa desde o ano de 2014.",
            "Fui o craque da Copa do Mundo sub 17, no ano de 2007.",
            "Fui campeão da Champions League, vestindo a camisa de 2 clubes diferentes.",
            "Sou patrocinado pela Adidas.",
            "Sou penta campeão do mundial de clubes."
        ],
        "difficulty": 4
    },
    # Jogador 7
    {
        "theme": "jogador_atividade",
        "title": "Jogador 7 - Sadio Mane",
        "answer": "Sadio Mane",
        "hints": [
            "Fui uma vez campeão da Champions League, vestindo a camisa de um time Inglês.",
            "Fui artilheiro da Premier League, na temporada 2018/19.",
            "Poderia ter sido jogador do Botafogo, ou ter jogado ao lado de Pelé.",
            "Ja marquei gol em final de Champions League, porém sai derrotado.",
            "Atualmente visto a camisa de número 10, no meu clube, e na minha seleção.",
            "Nasci no ano de 1992.",
            "Na temporada 2014/15, marquei um hat trick, com a incrível diferença de apenas 176 segundos, entre meu primeiro, e terceiro gol.",
            "O primeiro título que conquistei na minha carreira profissional, foi vestindo a camisa do Red Bull Salfzburg.",
            "Ja fui campeão austríaco, e inglês.",
            "Disputei a Copa do Mundo de 2018, inclusive como capitão."
        ],
        "difficulty": 4
    },
    # Jogador 8
    {
        "theme": "jogador_atividade",
        "title": "Jogador 8 - Lucas Lima",
        "answer": "Lucas Lima",
        "hints": [
            "Sou 'Xará', de um musico famoso.",
            "Meu sobrenome é 'Xará', de uma capital nacional.",
            "Ja marquei gols na La Bombonera, e no Monumental de Nunez.",
            "Ja fui campeão vestindo as camisas de Palmeiras, e Santos.",
            "Já fui uma vez campeão brasileiro, título esse conquistado vestindo a camisa do Palmeiras.",
            "Sou canhoto.",
            "Ja fui camisa 10 sa seleção brasileira, em uma competição oficial.",
            "Nasci na cidade de Marilia.",
            "Ja fui campeão gaúcho, e paulista.",
            "Nasci no ano de 1990."
        ],
        "difficulty": 3
    },
    # Jogador 9
    {
        "theme": "jogador_atividade",
        "title": "Jogador 9 - Sergio Ramos",
        "answer": "Sergio Ramos",
        "hints": [
            "Fui revelado pelo Sevilla.",
            "Já fui treinado por Vanderlei Luxemburgo.",
            "Marquei gols em 17 temporadas seguidas, do Campeonato Espanhol.",
            "Marquei gol, em duas finais diferentes de Champions League.",
            "Sou bicampeão da Eurocopa.",
            "Profissionalmente vesti a camisa de apenas 2 clubes.",
            "Nasci no ano de 1986.",
            "Visto a mesma camisa desde o ano de 2005.",
            "Disputei 4 Copas do Mundo.",
            "Ja fui uma vez campeão, da Copa do Mundo."
        ],
        "difficulty": 3
    },
    # Jogador 10
    {
        "theme": "jogador_atividade",
        "title": "Jogador 10 - Cristiano Ronaldo",
        "answer": "Cristiano Ronaldo",
        "hints": [
            "Já fui parceiro de ataque do ex atacante brasileiro Mario Jardel.",
            "Fui vencedor da primeira edição do prêmio Puskas.",
            "Ja fui treinado por Luis Felipe Scolari.",
            "Ja fui campeão da Champions League, vestindo a camisa de 2 times diferentes.",
            "Fui campeão europeu de clubes, e seleções no mesmo ano.",
            "Nasci no ano de 1985.",
            "Ja disputei os jogos olímpicos de 2004.",
            "Ja marquei 7 gols, em Copas do Mundo.",
            "Profissionalmente ja vesti 3 números diferentes de camisa, de forma oficial.",
            "Meu primeiro número oficial de camisa, foi a 28."
        ],
        "difficulty": 4
    },
    # Jogador 11
    {
        "theme": "jogador_atividade",
        "title": "Jogador 11 - Griezmann",
        "answer": "Griezmann",
        "hints": [
            "Em 2016, fui vice campeão Europeu de clubes, e seleções.",
            "Fui revelado pela Real Sociedade.",
            "Nunca atuei por um clube do meu país natal.",
            "Venci uma Copa do Mundo, inclusive marcando um gol na final.",
            "Fui campeão da Europa League, vestindo a camisa do Atlético de Madrid.",
            "Fui artilheiro da Eurocopa 2016.",
            "Nasci no ano de 1991.",
            "Sou canhoto.",
            "Sou o primeiro jogador da história das Copas do Mundo, a marcar um gol com o auxílio do VAR.",
            "Disputei duas Copas do Mundo."
        ],
        "difficulty": 4
    },
    # Jogador 12
    {
        "theme": "jogador_atividade",
        "title": "Jogador 12 - Haaland",
        "answer": "Haaland",
        "hints": [
            "Nasci no ano de 2000.",
            "Meu pai também foi jogador.",
            "Nasci no Norte da Europa.",
            "Tenho dupla nacionalidade.",
            "Em minha primeira participação na Champions League, marquei 10 gols.",
            "Meu primeiro título como profissional, foi vestindo a camisa do Red Bull Salzburg.",
            "Fui artilheiro da Copa do Mundo sub 20, no ano de 2019.",
            "Sou atacante.",
            "Em uma partida valida pela Copa do Mundo sub 20, marquei incríveis 9 gols.",
            "Sou canhoto."
        ],
        "difficulty": 3
    },
    # Jogador 13
    {
        "theme": "jogador_atividade",
        "title": "Jogador 13 - Neuer",
        "answer": "Neuer",
        "hints": [
            "Apesar de ser goleiro já cobrei um pênalti, em uma final de Champions League, em uma final decidida por penaltis.",
            "Fiz a narração do personagem Frank McCay na animação da Disney em 2013, para o meu país.",
            "Ja fui campeão da Copa do Mundo.",
            "Além de ser companheiro de classe de Ozil, também começamos no mesmo clube.",
            "Ja fui eleito o terceiro melhor jogador do mundo.",
            "Disputei 17 partidas, em Copas do Mundo.",
            "Já sofri um gol, do meio de campo.",
            "Ja defendi um penalti de Rogério Ceni.",
            "Ja fui duas vezes campeão da Champions League.",
            "Nasci no ano de 1986."
        ],
        "difficulty": 4
    },
    # Jogador 14
    {
        "theme": "jogador_atividade",
        "title": "Jogador 14 - Mandzukic",
        "answer": "Mandzukic",
        "hints": [
            "Marquei um gol, em final de Copa do Mundo.",
            "Sou penta campeão Italiano, e bicampeão Alemão.",
            "Nasci no Leste Europeu.",
            "Meu titulo mais importante é uma Champions League, vestindo uma camisa do Bayern de Munique, nessa conquista marquei um gol na final.",
            "Marquei gols em duas finais diferentes de Champions League, em 2013, e 2017.",
            "Fui vice campeão de uma Champions League, e Copa do Mundo, em anos consecutivos.",
            "Após a Copa do Mundo de 2018, anunciei minha aposentadoria, da minha seleção.",
            "Fui premiado com o gol mais bonito da UEFA, na temporada 2016/17.",
            "Nasci no ano de 1986.",
            "Sou atacante."
        ],
        "difficulty": 3
    },
    # Jogador 15
    {
        "theme": "jogador_atividade",
        "title": "Jogador 15 - Vardy",
        "answer": "Vardy",
        "hints": [
            "Nasci no ano de 1987.",
            "Fui o primeiro jogador a marcar gols, em 11 jogos seguidos do campeonato inglês.",
            "Fui artilheiro do campeonato inglês, na temporada 2019/20.",
            "Em 2007 fui preso, devido a uma briga em um bar, onde fui defender um amigo, e passei 6 meses em prisão domiciliar.",
            "Fui revelado pelo Stocksbridge Park.",
            "Disputei a Eurocopa 2016, e a Copa do Mundo 2018.",
            "Fui campeão ingles, vestindo a camisa do Leicester.",
            "Atualmente(2020/21), visto a camisa a mesma desde a temporada 2012/13.",
            "Sou atacante.",
            "Fui campeão da segunda divisão do campeonato inglês, na temporada 2013/14."
        ],
        "difficulty": 3
    },
    # Jogador 16
    {
        "theme": "jogador_atividade",
        "title": "Jogador 16 - Diego Carlos",
        "answer": "Diego Carlos",
        "hints": [
            "Nasci no ano de 1993.",
            "Sou zagueiro.",
            "Ja vesti a camisa do Nantes.",
            "Meu primeiro título como profissional, foi a Liga Europa, conquistada na temporada 2019/20.",
            "Fui revelado pelo Desportivo Brasil.",
            "Ja fui 'agredido' por um árbitro, que julgou que eu tinha o derrubado intencionalmente.",
            "Tive uma rápida passagem pelo São Paulo, no ano de 2013.",
            "Ja fui uma vez campeão da Liga Europa vestindo a camisa do Sevilla, inclusive marcando um gol de bicicleta na final.",
            "Nasci em Barra Bonita-SP.",
            "Tenho 1,86 de altura."
        ],
        "difficulty": 3
    }
]

with app.app_context():
    cards = [Card(theme=c["theme"], title=c["title"], answer=c["answer"],
                  hints_json=json.dumps(c["hints"]), difficulty=c["difficulty"]) for c in cards_data]
    db.session.add_all(cards)
    db.session.commit()
    print("Todos os 16 jogadores foram adicionados com sucesso!")

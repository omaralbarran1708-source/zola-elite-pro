export const demoFixtures = [
  {
    id: 1,
    competition: { name: 'CONMEBOL Libertadores', logo: 'https://media.api-sports.io/football/leagues/13.png' },
    status: { short: 'LIVE', elapsed: 66, long: 'Second Half' },
    home: { name: 'Flamengo', logo: 'https://media.api-sports.io/football/teams/127.png' },
    away: { name: 'Boca Juniors', logo: 'https://media.api-sports.io/football/teams/161.png' },
    goals: { home: 2, away: 1 },
    stats: { possession:[61,39], shots:[12,6], shotsOnTarget:[6,3], corners:[5,2], xg:[1.87,0.92] },
    momentum: [-1,0,1,2,1,3,4,5,3,1,-1,2,0,-2,-1,2,3,1,0,4,5,6,3,2,1,0,-1],
    timeline: [
      { minute:"65'", type:'red', title:'Expulsión Boca Juniors', detail:'Roja directa para Figal por juego brusco grave.'},
      { minute:"63'", type:'goal', title:'Gol Flamengo', detail:'Pedro marca el 2-1 con asistencia de Gerson.'},
      { minute:"41'", type:'goal', title:'Gol Boca Juniors', detail:'Merentiel anota el empate parcial.'}
    ],
    scorers: ["18' G. De Arrascaeta", "63' Pedro", "41' M. Merentiel"]
  },
  {
    id: 2,
    competition: { name: 'UEFA Champions League', logo: 'https://media.api-sports.io/football/leagues/2.png' },
    status: { short: 'LIVE', elapsed: 66, long: 'Second Half' },
    home: { name: 'Real Madrid', logo: 'https://media.api-sports.io/football/teams/541.png' },
    away: { name: 'Manchester City', logo: 'https://media.api-sports.io/football/teams/50.png' },
    goals: { home: 2, away: 1 },
    stats: { possession:[48,52], shots:[10,13], shotsOnTarget:[5,6], corners:[4,6], xg:[1.52,1.61] },
    momentum: [0,1,1,2,1,0,-1,0,1,2,3,4,2,1,0,-1,-2,-1,0,1,2,1,0,-1],
    timeline: [],
    scorers: []
  },
  {
    id: 3,
    competition: { name: 'FIFA World Cup', logo: 'https://media.api-sports.io/football/leagues/1.png' },
    status: { short: 'NS', elapsed: 0, long: 'Not Started' },
    home: { name: 'Argentina', logo: 'https://media.api-sports.io/football/teams/26.png' },
    away: { name: 'France', logo: 'https://media.api-sports.io/football/teams/2.png' },
    goals: { home: 0, away: 0 },
    stats: { possession:[50,50], shots:[0,0], shotsOnTarget:[0,0], corners:[0,0], xg:[0.95,1.05] },
    momentum: [0,0,0,0,0,0],
    timeline: [],
    scorers: []
  }
]

export const demoUpcoming = [
  { id: 101, competition: 'UEFA Champions League', match: 'Inter vs Napoli', time: 'Mañana 17:30' },
  { id: 102, competition: 'CONMEBOL Libertadores', match: 'River Plate vs Palmeiras', time: 'Mañana 19:00' },
  { id: 103, competition: 'FIFA World Cup', match: 'Brazil vs Germany', time: 'Vie 20:00' }
]

export const demoHistory = [
  { date:'20/04', market:'Over 2.5', odds:1.72, stake:10, result:'WIN', profit:7.20 },
  { date:'19/04', market:'BTTS Sí', odds:1.80, stake:15, result:'WIN', profit:12.00 },
  { date:'18/04', market:'Under 3.5', odds:1.90, stake:10, result:'LOSS', profit:-10.00 },
  { date:'17/04', market:'Over 1.5 HT', odds:1.70, stake:10, result:'WIN', profit:7.00 }
]

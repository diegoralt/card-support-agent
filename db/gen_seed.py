import random, datetime as dt
random.seed(26)
clientes = [  # id, nombre, email, kyc, ultimos4, limite
    (1, "Mariana Solís Ferrer", "mariana.solis@example.com", "aprobado", "4821", 45000),
    (2, "Joaquín Treviño Luna", "joaquin.trevino@example.com", "aprobado", "7390", 30000),
    (3, "Renata Aguilar Pineda", "renata.aguilar@example.com", "pendiente", "1567", 5000),
    (4, "Emilio Cárdenas Ruiz", "emilio.cardenas@example.com", "aprobado", "9034", 80000),
    (5, "Valeria Ochoa Domínguez", "valeria.ochoa@example.com", "aprobado", "2248", 25000),
    (6, "Tomás Ibarra Quintero", "tomas.ibarra@example.com", "aprobado", "6612", 60000),
]
comercios = [("OXXO", 40, 250), ("Walmart Supercenter", 300, 2200), ("Soriana", 250, 1800),
    ("Uber Trip", 60, 320), ("DiDi Food", 150, 480), ("Liverpool", 600, 4500), ("Farmacias Guadalajara", 80, 650), ("Pemex Gasolinera", 500, 1200),
    ("Cinépolis", 180, 420), ("Starbucks", 75, 190), ("Amazon México", 250, 3200),
    ("Mercado Libre", 200, 2800), ("Telcel Recarga", 100, 300), ("CFE Pago Luz", 350, 900)]
# un cargo "no reconocido" plausible por cliente (fecha, comercio, monto)
sospechosos = {1: ("2026-09-12", "GPLAY*APPSTORE HK", 1899.00), 2: ("2026-09-03", "MERPAGO*ELECTRONICA", 4350.00),
    3: ("2026-09-18", "PAYPAL *GAMESHOP", 899.00), 4: ("2026-09-08", "AMZN MKTP US", 6420.50),
    5: ("2026-09-15", "SPOTIFY P2A91C", 129.00), 6: ("2026-09-21", "INTL WIRE SVC LTD", 2750.00)}
ini = dt.date(2026, 8, 27)
out = ["-- Datos 100 % sintéticos generados con semilla fija (gen_seed.py, random.seed(26)).",
"-- Periodo: 2026-08-27 a 2026-09-25. Corte: día 5; límite de pago: día 25.",
"-- Cargos 'no reconocidos' plantados (para evals):"]
out += [f"--   cliente {c}: {f} {m} ${a:,.2f}" for c, (f, m, a) in sospechosos.items()]
out += ["", "insert into customers (id, nombre, email, kyc_status) values"]
out += [",\n".join(f"  ({i}, '{n}', '{e}', '{k}')" for i, n, e, k, _, _ in clientes) + ";", ""]
out += ["insert into cards (id, customer_id, ultimos4, estado, limite_credito) values"]
out += [",\n".join(f"  ({i}, {i}, '{u}', 'activa', {l})" for i, _, _, _, u, l in clientes) + ";", ""]
rows = []
for cid, *_ in clientes:
    tx = []
    # cliente 3 tiene KYC pendiente: la política limita sus compras a $5,000 al mes
    pool = [x for x in comercios if x[2] <= 650] if cid == 3 else comercios
    for _ in range(6 if cid == 3 else random.randint(16, 22)):
        c, lo, hi = random.choice(pool)
        tx.append((ini + dt.timedelta(days=random.randint(0, 29)), c, round(random.uniform(lo, hi), 2), "compra"))
    tx.append((dt.date(2026, 9, 10), "Spotify", 129.00, "compra"))  # suscripción: una vez al mes
    if cid % 2: tx.append((dt.date(2026, 9, 2), "Netflix", 299.00, "compra"))
    tx.append((dt.date(2026, 8, 30), "PAGO SPEI RECIBIDO", -round(random.uniform(2000, 9000), 2), "pago"))
    f, m, a = sospechosos[cid]
    tx.append((dt.date.fromisoformat(f), m, a, "compra"))
    rows += [f"  ({cid}, '{d}', '{m}', {a:.2f}, '{t}')" for d, m, a, t in sorted(tx)]
out += ["insert into transactions (card_id, fecha, comercio, monto, tipo) values", ",\n".join(rows) + ";"]
open(__file__.replace("gen_seed.py", "seed.sql"), "w").write("\n".join(out) + "\n")
print(len(rows), "transacciones")

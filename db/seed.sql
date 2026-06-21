-- Seed idempotente — dados de base que todo banco limpo precisa.
-- Categorias autorizadas (espelha CATEGORIAS_AUTORIZADAS em src/carteirai/dominio/dtos.py).

INSERT INTO categorias (nome, tipo) VALUES
    ('Alimentação',          'despesa'),
    ('Mercado',              'despesa'),
    ('Transporte',           'despesa'),
    ('Moradia',              'despesa'),
    ('Saúde',                'despesa'),
    ('Educação',             'despesa'),
    ('Lazer',                'despesa'),
    ('Assinaturas',          'despesa'),
    ('Vestuário',            'despesa'),
    ('Lanche na rua',        'despesa'),
    ('Presentes',            'despesa'),
    ('Pix',                  'despesa'),
    ('Transferências',       'despesa'),
    ('Investimentos/Reserva','despesa'),
    ('Outros',               'despesa')
ON CONFLICT (nome) DO NOTHING;

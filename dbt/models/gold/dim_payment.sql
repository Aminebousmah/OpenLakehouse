select payment_type, payment_label
from (
    values
        (0, 'Non renseigné'),
        (1, 'Carte bancaire'),
        (2, 'Espèces'),
        (3, 'Gratuit'),
        (4, 'Litige'),
        (5, 'Inconnu'),
        (6, 'Trajet annulé')
) as t (payment_type, payment_label)

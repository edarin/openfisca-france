# -*- coding: utf-8 -*-

from copy import deepcopy

from openfisca_core.taxbenefitsystems import TaxBenefitSystem
from openfisca_core.variables import Variable
from openfisca_core.columns import FloatCol, IntCol, BoolCol
from openfisca_core.tools import assert_near

from openfisca_france.scenarios import Scenario
from openfisca_france.entities import entities, Individu, Famille, FoyerFiscal, Menage
from openfisca_france.model.base import *  # noqa analysis:ignore


class af(Variable):
    column = FloatCol
    entity = Famille

class salaire(Variable):
    column = FloatCol
    entity = Individu

class age(Variable):
    column = IntCol
    entity = Individu

class autonomie_financiere(Variable):
    column = BoolCol
    entity = Individu

class depcom(Variable):
    column = FixedStrCol(max_length = 5)
    entity = Menage
    is_permanent = True
    label = u"""Code INSEE "depcom" de la commune de résidence de la famille"""

# This tests are more about core than france, but we need france entities to run some of them.
# We use a dummy TBS to run the tests faster
class DummyTaxBenefitSystem(TaxBenefitSystem):
    def __init__(self):
        TaxBenefitSystem.__init__(self, entities)
        self.Scenario = Scenario
        self.add_variables(af, salaire, age, autonomie_financiere, depcom)

tax_benefit_system = DummyTaxBenefitSystem()

TEST_CASE = {
    'individus': [{'id': 'ind0'}, {'id': 'ind1'}, {'id': 'ind2'}, {'id': 'ind3'},{'id': 'ind4'}, {'id': 'ind5'}],
    'familles': [
        {'enfants': ['ind2', 'ind3'], 'parents': ['ind0', 'ind1']},
        {'enfants': ['ind5'], 'parents': ['ind4']}
        ],
    'foyers_fiscaux': [
        {'declarants': ['ind0', 'ind1'], 'personnes_a_charge': ['ind2', 'ind3']},
        {'personnes_a_charge': ['ind5'], 'declarants': ['ind4']}
        ],
    'menages': [
        {'conjoint': 'ind1', 'enfants': ['ind2', 'ind3'], 'personne_de_reference': 'ind0'},
        {'conjoint': None, 'enfants': ['ind5'], 'personne_de_reference': 'ind4'},
        ],
    }

TEST_CASE_AGES = deepcopy(TEST_CASE)
AGES = [40, 37, 7, 9, 54, 20]
for (individu, age) in zip(TEST_CASE_AGES['individus'], AGES):
        individu['age'] = age

def new_simulation(test_case):
    return tax_benefit_system.new_scenario().init_from_test_case(
        period = 2013,
        test_case = test_case
    ).new_simulation()


def test_transpose():
    test_case = deepcopy(TEST_CASE)
    test_case['familles'][0]['af'] = 20000
    test_case['familles'][1]['af'] = 10000
    test_case['foyers_fiscaux'] = [
        TEST_CASE['foyers_fiscaux'][0],
        {'declarants': ['ind4']},
        {'declarants': ['ind5']}
        ]

    simulation = new_simulation(test_case)
    foyer_fiscal = simulation.foyer_fiscal

    af_foyer_fiscal = foyer_fiscal.first_person.famille('af')

    assert_near(af_foyer_fiscal, [20000, 10000, 10000])

def test_transpose_string():
    test_case = deepcopy(TEST_CASE)
    test_case['menages'][0]['depcom'] = "93400"
    test_case['menages'][1]['depcom'] = "89300"

    simulation = new_simulation(test_case)
    famille = simulation.famille

    depcom_famille = famille.first_person.menage('depcom')

    assert((depcom_famille == ["93400", "89300"]).all())

def test_value_from_person():
    test_case = deepcopy(TEST_CASE_AGES)
    simulation = new_simulation(test_case)

    foyer_fiscal = simulation.foyer_fiscal
    age = foyer_fiscal.members('age')

    age_conjoint = foyer_fiscal.conjoint('age')
    assert_near(age_conjoint, [37, 0])

def test_combination_projections():
    test_case = deepcopy(TEST_CASE_AGES)
    simulation = new_simulation(test_case)

    individu = simulation.persons

    age_parent1 = individu.famille.demandeur('age')

    assert_near(age_parent1, [40, 40, 40, 40, 54, 54])

def test_complex_chain_2():
    test_case = {
        'individus': [
            {'id': 'ind0', 'age': 30}, {'id': 'ind1', 'age': 31}, {'id': 'ind2', 'age': 32}, {'id': 'ind3', 'age': 33}
            ],
        'familles': [
            {'parents': ['ind0', 'ind1']},
            {'parents': ['ind2']},
            {'parents': ['ind3']},
            ],
        'foyers_fiscaux': [
            {'declarants': ['ind0', 'ind1']},
            {'declarants': ['ind2', 'ind3']},
            ],
        'menages': [
            {'personne_de_reference': 'ind0'},
            {'personne_de_reference': 'ind1', 'autres': 'ind2'},
            {'personne_de_reference': 'ind3'},
            ],
        }


    simulation = new_simulation(test_case)

    assert_near(simulation.famille.demandeur.menage.personne_de_reference('age'), [30, 31, 33])
    assert_near(simulation.famille.conjoint.menage.personne_de_reference('age'), [31, 0, 0])
    assert_near(simulation.famille.demandeur.foyer_fiscal.declarant_principal('age'), [30, 32, 32])
    assert_near(simulation.foyer_fiscal.conjoint.famille.demandeur('age'), [30, 33])

import os
from frag.network.decorate import get_3d_vects_for_mol, get_vect_indices_for_mol
from frag.network.query import get_full_graph
#L+
from urllib.parse import urljoin

from api.utils import draw_mol

from viewer.models import (
    ActivityPoint,
    Molecule,
    Project,
    Protein,
    Compound,
    Target,
    Snapshot,
    SessionProject,
    ActionType,
    SnapshotActions,
    SessionActions,
    ComputedMolecule,
    ComputedSet,
    NumericalScoreValues,
    ScoreDescription,
    File,
    TextScoreValues
)

from django.contrib.auth.models import User
#L+
from django.conf import settings

from rest_framework import serializers

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = "__all__"

def get_protein_sequences(pdb_block):
    sequence_list = []
    aa = {'CYS': 'C', 'ASP': 'D', 'SER': 'S', 'GLN': 'Q', 'LYS': 'K',
          'ILE': 'I', 'PRO': 'P', 'THR': 'T', 'PHE': 'F', 'ASN': 'N',
          'GLY': 'G', 'HIS': 'H', 'LEU': 'L', 'ARG': 'R', 'TRP': 'W',
          'ALA': 'A', 'VAL': 'V', 'GLU': 'E', 'TYR': 'Y', 'MET': 'M'}

    current_chain = 'A'
    current_sequence = ''
    current_number = 0

    for line in pdb_block.split('\n'):

        if line[0:4] == 'ATOM':
            residue = line[17:20].strip()
            chain = line[21].strip()
            n = int(line[22:26].strip())

            if chain != current_chain:
                chain_dict = {'chain': current_chain, 'sequence': current_sequence}
                sequence_list.append(chain_dict)
                current_sequence = ''
                current_chain = chain
            if not n == current_number:
                if n == current_number + 1:
                    try:
                        seqres = aa[residue]
                    except:
                        seqres = 'X'
                    current_sequence += seqres
                else:
                    if not current_number == 0:
                        gap = n - current_number
                        gap_str = ''
                        for i in range(0, gap):
                            gap_str += 'X'
                        current_sequence += gap_str
            current_number = n

    if not sequence_list:
        chain_dict = {'chain': current_chain, 'sequence': current_sequence}
        sequence_list.append(chain_dict)

    return sequence_list


class TargetSerializer(serializers.ModelSerializer):
    template_protein = serializers.SerializerMethodField()
    zip_archive = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()
    sequences = serializers.SerializerMethodField()

    def get_template_protein(self, obj):
        proteins = obj.protein_set.filter()
        for protein in proteins:
            if protein.pdb_info:
                return protein.pdb_info.url
        return "NOT AVAILABLE"

    def get_zip_archive(self, obj):
        request = self.context["request"]
        # This is to map links to HTTPS to avoid Mixed Content warnings from Chrome browsers
        # SECURE_PROXY_SSL_HEADER is referenced because it is used in redirecting URLs - if
        # it is changed it may affect this code.
        # Using relative links will probably also work, but This workaround allows both the
        # 'download structures' button and the DRF API call to work.
        # The if-check is because the filefield in target has null=True.
        # Note that this link will not work on local
        https_host = settings.SECURE_PROXY_SSL_HEADER[1] + '://' + request.get_host()
        if hasattr(obj, 'zip_archive') and obj.zip_archive.name:
            return urljoin(https_host, obj.zip_archive.url)
        else:
            return

    def get_metadata(self, obj):
        request = self.context["request"]
        # This is to map links to HTTPS to avoid Mixed Content warnings from Chrome browsers
        # See above for details.
        https_host = settings.SECURE_PROXY_SSL_HEADER[1] + '://' + request.get_host()
        if hasattr(obj, 'metadata') and obj.metadata.name:
            return urljoin(https_host, obj.metadata.url)
        else:
            return

    def get_sequences(self, obj):
        proteins = obj.protein_set.filter()
        protein_file = None
        for protein in proteins:
            if protein.pdb_info:
                if not os.path.isfile(protein.pdb_info.path):
                    continue
                protein_file = protein.pdb_info
                break
        if not protein_file:
            return [{'chain': '', 'sequence': ''}]

        protein_file.open(mode='r')
        pdb_block = protein_file.read()
        protein_file.close()

        sequences = get_protein_sequences(pdb_block)
        return sequences

    class Meta:
        model = Target
        fields = ("id", "title", "project_id", "protein_set", "template_protein", "metadata", "zip_archive", "sequences")


class CompoundSerializer(serializers.ModelSerializer):

    class Meta:
        model = Compound
        fields = (
            "id",
            "inchi",
            "long_inchi",
            "smiles",
            "current_identifier",
            "all_identifiers",
            # "project_id",
            "mol_log_p",
            "mol_wt",
            "tpsa",
            "heavy_atom_count",
            "heavy_atom_mol_wt",
            "nhoh_count",
            "no_count",
            "num_h_acceptors",
            "num_h_donors",
            "num_het_atoms",
            "num_rot_bonds",
            "num_val_electrons",
            "ring_count",
            # "inspirations",
            # "description",
            # "comments",
        )


class MoleculeSerializer(serializers.ModelSerializer):

    molecule_protein = serializers.SerializerMethodField()
    protein_code = serializers.SerializerMethodField()
    mw = serializers.SerializerMethodField()
    logp = serializers.SerializerMethodField()
    tpsa = serializers.SerializerMethodField()
    ha = serializers.SerializerMethodField()
    hacc = serializers.SerializerMethodField()
    hdon = serializers.SerializerMethodField()
    rots = serializers.SerializerMethodField()
    rings = serializers.SerializerMethodField()
    velec = serializers.SerializerMethodField()


    def get_molecule_protein(self, obj):
        return obj.prot_id.pdb_info.url

    def get_protein_code(self, obj):
        return obj.prot_id.code

    def get_mw(self, obj):
        return round(obj.cmpd_id.mol_wt, 2)

    def get_logp(self, obj):
        return round(obj.cmpd_id.mol_log_p, 2)

    def get_tpsa(self, obj):
        return round(obj.cmpd_id.tpsa, 2)

    def get_ha(self, obj):
        return obj.cmpd_id.heavy_atom_count

    def get_hacc(self, obj):
        return obj.cmpd_id.num_h_acceptors

    def get_hdon(self, obj):
        return obj.cmpd_id.num_h_donors

    def get_rots(self, obj):
        return obj.cmpd_id.num_rot_bonds

    def get_rings(self, obj):
        return obj.cmpd_id.ring_count

    def get_velec(self, obj):
        return obj.cmpd_id.num_val_electrons

    class Meta:
        model = Molecule
        fields = (
            "id",
            "smiles",
            "cmpd_id",
            "prot_id",
            "protein_code",
            "mol_type",
            "molecule_protein",
            "lig_id",
            "chain_id",
            "sdf_info",
            "x_com",
            "y_com",
            "z_com",
            "mw",
            "logp",
            "tpsa",
            "ha",
            "hacc",
            "hdon",
            "rots",
            "rings",
            "velec"
        )


class ActivityPointSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityPoint
        fields = (
            "id",
            "source",
            "target_id",
            "cmpd_id",
            "activity",
            "units",
            "confidence",
            "operator",
            "internal_id",
        )


class ProteinSerializer(serializers.ModelSerializer):

    class Meta:
        model = Protein
        fields = (
            "id",
            "code",
            "target_id",
            "prot_type",
            "pdb_info",
            "bound_info",
            "mtz_info",
            "map_info",
            "cif_info",
        )


class ProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project
        fields = ("id", "title")


class MolImageSerialzier(serializers.ModelSerializer):

    mol_image = serializers.SerializerMethodField()

    def get_mol_image(self, obj):
        request = self.context["request"]
        params = request.query_params
        if params:
            return draw_mol(
                obj.smiles,
                height=int(float(params["height"])),
                width=int(float(params["width"])),
            )
        else:
            return draw_mol(obj.smiles, height=125, width=125)

    class Meta:
        model = Molecule
        fields = ("id", "mol_image")


class CmpdImageSerialzier(serializers.ModelSerializer):

    cmpd_image = serializers.SerializerMethodField()

    def get_cmpd_image(self, obj):
        return draw_mol(obj.smiles, height=125, width=125)

    class Meta:
        model = Compound
        fields = ("id", "cmpd_image")


class ProtMapInfoSerialzer(serializers.ModelSerializer):

    map_data = serializers.SerializerMethodField()

    def get_map_data(self, obj):
        if obj.map_info:
            return open(obj.map_info.path).read()
        else:
            return None

    class Meta:
        model = Protein
        fields = ("id", "map_data", "prot_type")


class ProtPDBInfoSerialzer(serializers.ModelSerializer):

    pdb_data = serializers.SerializerMethodField()

    def get_pdb_data(self, obj):
        return open(obj.pdb_info.path).read()


    class Meta:
        model = Protein
        fields = ("id", "pdb_data", "prot_type")


class ProtPDBBoundInfoSerialzer(serializers.ModelSerializer):

    bound_pdb_data = serializers.SerializerMethodField()

    def get_bound_pdb_data(self, obj):
        if obj.bound_info:
            return open(obj.bound_info.path).read()
        else:
            return None

    class Meta:
        model = Protein
        fields = ("id", "bound_pdb_data", "target_id")


class VectorsSerializer(serializers.ModelSerializer):

    vectors = serializers.SerializerMethodField()

    def get_vectors(self, obj):
        out_data = {}
        try:
            out_data["3d"] = get_3d_vects_for_mol(obj.sdf_info, iso_labels=False)
        # temporary patch
        except IndexError:
            out_data["3d"] = get_3d_vects_for_mol(obj.sdf_info, iso_labels=True)
        out_data["indices"] = get_vect_indices_for_mol(obj.sdf_info)
        return out_data

    class Meta:
        model = Molecule
        fields = ("id", "vectors")


class GraphSerializer(serializers.ModelSerializer):

    graph = serializers.SerializerMethodField()
    graph_choice = os.environ.get("NEO4J_QUERY", "neo4j")
    graph_auth = os.environ.get("NEO4J_AUTH", "neo4j/neo4j")

    def get_graph(self, obj):
        return get_full_graph(obj.smiles, self.graph_choice, self.graph_auth,
                              isomericSmiles=True)

    class Meta:
        model = Molecule
        fields = ("id", "graph")


### Start of Session Project
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


# GET
class ActionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionType
        fields = '__all__'


# GET
class SessionProjectReadSerializer(serializers.ModelSerializer):
    target = TargetSerializer(read_only=True)
    author = UserSerializer(read_only=True)
    class Meta:
        model = SessionProject
        fields = '__all__'


# (POST, PUT, PATCH)
class SessionProjectWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionProject
        fields = '__all__'


# (GET, POST, PUT, PATCH)
class SessionActionsSerializer(serializers.ModelSerializer):
    actions = serializers.JSONField()
    class Meta:
        model = SessionActions
        fields = '__all__'


# GET
class SnapshotReadSerializer(serializers.ModelSerializer):
    author  = UserSerializer()
    session_project  = SessionProjectWriteSerializer()
    class Meta:
        model = Snapshot
        fields = ('id', 'type', 'title', 'author', 'description', 'created', 'data', 'session_project', 'parent', 'children')


# (POST, PUT, PATCH)
class SnapshotWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = ('id', 'type', 'title', 'author', 'description', 'created', 'data', 'session_project', 'parent', 'children')
## End of Session Project


# (GET, POST, PUT, PATCH)
class SnapshotActionsSerializer(serializers.ModelSerializer):
    actions = serializers.JSONField()
    class Meta:
        model = SnapshotActions
        fields = '__all__'


## End of Session Project
# class FileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ComputedMolecule
#         fields = "__all__"

class ComputedSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputedSet
        fields = '__all__'


class ComputedMoleculeSerializer(serializers.ModelSerializer):
    # performance issue
    # inspiration_frags = MoleculeSerializer(read_only=True, many=True)
    class Meta:
        model = ComputedMolecule
        fields = '__all__'


class ScoreDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreDescription
        fields = '__all__'


class NumericalScoreSerializer(serializers.ModelSerializer):
    score = ScoreDescriptionSerializer(read_only=True)
    class Meta:
        model = NumericalScoreValues
        fields = '__all__'


class TextScoreSerializer(serializers.ModelSerializer):
    score = ScoreDescriptionSerializer(read_only=True)
    class Meta:
        model = TextScoreValues
        fields = '__all__'


class ComputedMolAndScoreSerializer(serializers.ModelSerializer):
    numerical_scores = serializers.SerializerMethodField()
    text_scores = serializers.SerializerMethodField()
    pdb_info = serializers.SerializerMethodField()
    # score_descriptions = serializers.SerializerMethodField()

    class Meta:
        model = ComputedMolecule
        fields = (
            "id",
            "sdf_info",
            "name",
            "smiles",
            "pdb_info",
            "compound",
            "computed_set",
            "computed_inspirations",
            "numerical_scores",
            "text_scores",
            # "score_descriptions",
        )

    def get_numerical_scores(self, obj):
        scores = NumericalScoreValues.objects.filter(compound=obj)
        score_dict = {}
        for score in scores:
            score_dict[score.score.name] = score.value
        return score_dict

    def get_text_scores(self, obj):
        scores = TextScoreValues.objects.filter(compound=obj)
        score_dict = {}
        for score in scores:
            score_dict[score.score.name] = score.value
        return score_dict

    def get_pdb_info(self, obj):
        if obj.pdb:
            return obj.pdb.pdb_info.url
        else:
            return None

    # def get_score_descriptions(self, obj):
    #     descriptions = ScoreDescription.objects.filter(computed_set=obj.computed_set)
    #     desc_dict = {}
    #     for desc in descriptions:
    #         desc_dict[desc.name] = desc.description
    #     return desc_dict

# Start of Discourse Serializer

# Class for customer Discourse API
class DiscoursePostWriteSerializer(serializers.Serializer):
    category_name = serializers.CharField(max_length=200)
    parent_category_name = serializers.CharField(max_length=200, initial=settings.DISCOURSE_PARENT_CATEGORY)
    category_colour = serializers.CharField(max_length=10, initial="0088CC")
    category_text_colour = serializers.CharField(max_length=10, initial="FFFFFF")
    post_title = serializers.CharField(max_length=200)
    post_content = serializers.CharField(max_length=2000)
    post_tags = serializers.JSONField()

# End of Discourse Serializer

# Serializer Class for DictToCsv API
class DictToCsvSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    dict = serializers.DictField()

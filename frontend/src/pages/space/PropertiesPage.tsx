import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Home, MapPin, Plus, Ruler, Wrench } from 'lucide-react';

import { ApiError, http } from '@/lib/api';
import { Seo } from '@/components/Seo';
import { Alert, CardSkeleton, EmptyState, ErrorState } from '@/components/ui/Feedback';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select, Textarea } from '@/components/ui/Field';
import { useMyProperties } from '@/lib/hooks';
import { formatDate, relativeTime } from '@/lib/format';
import { qk } from '@/lib/query';

const PROPERTY_TYPES = [
  { value: 'VILLA', label: 'Villa' },
  { value: 'MAISON', label: 'Maison' },
  { value: 'APPARTEMENT', label: 'Appartement' },
  { value: 'IMMEUBLE', label: 'Immeuble' },
  { value: 'LOCAL_COMMERCIAL', label: 'Local commercial' },
  { value: 'BUREAU', label: 'Bureau' },
  { value: 'TERRAIN', label: 'Terrain' },
  { value: 'ENTREPOT', label: 'Entrepôt' },
];

const OCCUPANCY = [
  { value: 'VACANT', label: 'Inoccupée' },
  { value: 'OCCUPIED_OWNER', label: 'Occupée par le propriétaire' },
  { value: 'RENTED', label: 'Louée' },
  { value: 'FAMILY', label: 'Occupée par la famille' },
  { value: 'GUARDED', label: 'Gardien sur place' },
];

const EMPTY_FORM = {
  name: '',
  property_type: 'VILLA',
  occupancy_status: 'VACANT',
  city: '',
  location_text: '',
  area_m2: '',
  rooms_count: '',
  estimated_value_xaf: '',
  monthly_rent_xaf: '',
  description: '',
};

export default function PropertiesPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useMyProperties();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const properties = data?.results ?? [];

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setServerError(null);

    const next: Record<string, string> = {};
    if (form.name.trim().length < 3) next.name = 'Donnez un nom à ce bien (ex. « Villa Akwa »).';
    if (!form.city.trim()) next.city = 'Indiquez la ville du bien.';
    if (!form.location_text.trim()) next.location_text = 'Précisez le quartier ou l\u2019adresse approximative.';
    if (form.monthly_rent_xaf && form.occupancy_status !== 'RENTED') {
      next.monthly_rent_xaf = 'Le loyer mensuel ne se renseigne que pour un bien loué.';
    }
    setErrors(next);
    if (Object.keys(next).length) return;

    setSubmitting(true);
    try {
      await http.post('/properties/', {
        name: form.name.trim(),
        property_type: form.property_type,
        occupancy_status: form.occupancy_status,
        city: form.city.trim(),
        location_text: form.location_text.trim(),
        country: 'CM',
        area_m2: form.area_m2 ? Number(form.area_m2) : null,
        rooms_count: form.rooms_count ? Number(form.rooms_count) : null,
        estimated_value_xaf: form.estimated_value_xaf || null,
        monthly_rent_xaf: form.occupancy_status === 'RENTED' && form.monthly_rent_xaf ? form.monthly_rent_xaf : null,
        description: form.description.trim(),
      });
      await queryClient.invalidateQueries({ queryKey: qk.myProperties() });
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setForm(EMPTY_FORM);
      setShowForm(false);
    } catch (error) {
      if (error instanceof ApiError) {
        setServerError(error.message);
        setErrors(
          Object.fromEntries(Object.entries(error.fields ?? {}).map(([field, messages]) => [field, messages[0]])),
        );
      } else {
        setServerError("L'ajout du bien a échoué. Réessayez dans un instant.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Seo
        title="Mes propriétés"
        description="Gérez votre patrimoine immobilier au Cameroun : état, occupation, valeur estimée, visites d'entretien et historique des interventions."
        path="/espace/proprietes"
        noIndex
      />

      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-[1.75rem]">Mes propriétés</h1>
            <p className="mt-1.5 text-[0.9375rem] text-k-muted">
              Enregistrez vos biens pour planifier les visites d&apos;entretien, suivre leur état et constituer un
              historique utile en cas de location ou de revente.
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => setShowForm((value) => !value)}
            icon={<Plus className="size-4" aria-hidden />}
          >
            {showForm ? 'Fermer le formulaire' : 'Ajouter un bien'}
          </Button>
        </header>

        {showForm ? (
          <form onSubmit={submit} noValidate className="rounded-k-lg border border-k-line bg-white p-5 sm:p-6">
            <h2 className="text-[1.125rem]">Nouveau bien</h2>
            <p className="mt-1 text-[0.875rem] text-k-muted">
              Seuls le nom, la ville et le quartier sont obligatoires : vous pourrez compléter le reste plus tard avec
              votre chargé de suivi.
            </p>

            {serverError ? (
              <Alert tone="error" className="mt-4">
                {serverError}
              </Alert>
            ) : null}

            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <Field label="Nom du bien" htmlFor="p-name" required error={errors.name}>
                <Input
                  id="p-name"
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  error={errors.name}
                  placeholder="Villa Bonapriso"
                />
              </Field>
              <Field label="Type de bien" htmlFor="p-type" required>
                <Select
                  id="p-type"
                  value={form.property_type}
                  onChange={(event) => setForm({ ...form, property_type: event.target.value })}
                >
                  {PROPERTY_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Ville" htmlFor="p-city" required error={errors.city}>
                <Input
                  id="p-city"
                  value={form.city}
                  onChange={(event) => setForm({ ...form, city: event.target.value })}
                  error={errors.city}
                  placeholder="Douala"
                />
              </Field>
              <Field label="Quartier / adresse" htmlFor="p-location" required error={errors.location_text}>
                <Input
                  id="p-location"
                  value={form.location_text}
                  onChange={(event) => setForm({ ...form, location_text: event.target.value })}
                  error={errors.location_text}
                  placeholder="Akwa, rue des Palmiers"
                />
              </Field>
              <Field label="Occupation" htmlFor="p-occupancy">
                <Select
                  id="p-occupancy"
                  value={form.occupancy_status}
                  onChange={(event) => setForm({ ...form, occupancy_status: event.target.value })}
                >
                  {OCCUPANCY.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Surface habitable" htmlFor="p-area" hint="En m²">
                <Input
                  id="p-area"
                  inputMode="numeric"
                  value={form.area_m2}
                  onChange={(event) => setForm({ ...form, area_m2: event.target.value.replace(/\D/g, '') })}
                  placeholder="240"
                />
              </Field>
              <Field label="Nombre de pièces" htmlFor="p-rooms">
                <Input
                  id="p-rooms"
                  inputMode="numeric"
                  value={form.rooms_count}
                  onChange={(event) => setForm({ ...form, rooms_count: event.target.value.replace(/\D/g, '') })}
                  placeholder="6"
                />
              </Field>
              <Field label="Valeur estimée" htmlFor="p-value" hint="En francs CFA, si vous la connaissez">
                <Input
                  id="p-value"
                  inputMode="numeric"
                  value={form.estimated_value_xaf}
                  onChange={(event) =>
                    setForm({ ...form, estimated_value_xaf: event.target.value.replace(/\D/g, '') })
                  }
                  placeholder="180 000 000"
                />
              </Field>
              {form.occupancy_status === 'RENTED' ? (
                <Field label="Loyer mensuel" htmlFor="p-rent" error={errors.monthly_rent_xaf} hint="En FCFA">
                  <Input
                    id="p-rent"
                    inputMode="numeric"
                    value={form.monthly_rent_xaf}
                    onChange={(event) =>
                      setForm({ ...form, monthly_rent_xaf: event.target.value.replace(/\D/g, '') })
                    }
                    error={errors.monthly_rent_xaf}
                    placeholder="450 000"
                  />
                </Field>
              ) : null}
            </div>

            <Field label="Notes internes" htmlFor="p-description" className="mt-5" hint="Visible uniquement par vous et l'équipe KEMTA">
              <Textarea
                id="p-description"
                rows={3}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                placeholder="Compteurs individuels, citerne de 5 000 litres, portail automatique à réviser."
              />
            </Field>

            <div className="mt-5 flex flex-wrap gap-3">
              <Button type="submit" loading={submitting}>
                Enregistrer le bien
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowForm(false);
                  setErrors({});
                  setServerError(null);
                }}
              >
                Annuler
              </Button>
            </div>
          </form>
        ) : null}

        {isError ? (
          <ErrorState message="Vos propriétés n'ont pas pu être chargées." onRetry={() => void refetch()} />
        ) : isLoading ? (
          <div className="grid gap-5 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <CardSkeleton key={index} lines={4} />
            ))}
          </div>
        ) : properties.length === 0 ? (
          <EmptyState
            icon={<Home className="size-5" aria-hidden />}
            title="Aucun bien enregistré"
            description="Ajoutez vos villas, immeubles ou locaux pour planifier les visites d'entretien et conserver l'historique des interventions."
            action={<Button onClick={() => setShowForm(true)}>Ajouter mon premier bien</Button>}
          />
        ) : (
          <div className="grid gap-5 md:grid-cols-2">
            {properties.map((property) => (
              <article
                key={property.id}
                className="flex flex-col overflow-hidden rounded-k-lg border border-k-line bg-white"
              >
                {property.cover_url ? (
                  <img
                    src={property.cover_url}
                    alt={property.name}
                    loading="lazy"
                    className="h-40 w-full object-cover"
                  />
                ) : (
                  <div className="k-grid-lines h-24 w-full bg-k-blue" aria-hidden />
                )}

                <div className="flex flex-1 flex-col p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="text-[1.0625rem]">{property.name}</h2>
                      <p className="mt-1 flex items-center gap-1.5 text-[0.75rem] text-k-muted">
                        <MapPin className="size-3" aria-hidden />
                        {property.display_location}
                      </p>
                      <p className="mt-0.5 text-[0.6875rem] text-k-muted">{property.reference}</p>
                    </div>
                    <StatusBadge code={property.occupancy_status} label={property.occupancy_label} />
                  </div>

                  <dl className="mt-4 grid grid-cols-2 gap-3 text-[0.75rem] sm:grid-cols-3">
                    <div>
                      <dt className="text-k-muted">Type</dt>
                      <dd className="font-medium text-k-ink">{property.type_label}</dd>
                    </div>
                    <div>
                      <dt className="text-k-muted">Surface</dt>
                      <dd className="inline-flex items-center gap-1 font-medium text-k-ink">
                        <Ruler className="size-3" aria-hidden />
                        {property.area_m2 ? `${Number(property.area_m2).toLocaleString('fr-FR')} m²` : '—'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-k-muted">Pièces</dt>
                      <dd className="font-medium text-k-ink">{property.rooms_count ?? '—'}</dd>
                    </div>
                  </dl>

                  <ul className="mt-4 flex flex-wrap gap-2">
                    {property.active_contract_label ? (
                      <li>
                        <Badge tone="blue" size="sm">
                          <Wrench className="size-3" aria-hidden />
                          {property.active_contract_label}
                        </Badge>
                      </li>
                    ) : (
                      <li>
                        <Badge tone="outline" size="sm">
                          Sans contrat d&apos;entretien
                        </Badge>
                      </li>
                    )}
                    {property.needs_attention ? (
                      <li>
                        <Badge tone="amber" size="sm">
                          <AlertTriangle className="size-3" aria-hidden />
                          Visite recommandée
                        </Badge>
                      </li>
                    ) : null}
                  </ul>

                  <p className="mt-auto pt-4 text-[0.75rem] text-k-muted">
                    Dernière visite :{' '}
                    {property.last_visited_at ? relativeTime(property.last_visited_at) : 'aucune visite enregistrée'}
                    {property.next_visit_at ? ` · Prochaine : ${formatDate(property.next_visit_at)}` : ''}
                  </p>
                </div>
              </article>
            ))}
          </div>
        )}

        <p className="text-[0.75rem] text-k-muted">
          Pour confier l&apos;entretien d&apos;un bien à KEMTA (visites périodiques, petits travaux, comptes rendus
          photo),{' '}
          <a href="/demande?service=entretien-propriete" className="font-medium text-k-blue hover:text-k-green-dark">
            créez une demande d&apos;entretien
          </a>
          .
        </p>
      </div>
    </>
  );
}

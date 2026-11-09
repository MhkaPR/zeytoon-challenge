import { CompanyRegistrationPage } from "@/src/features/company/CompanyRegistrationPage";

/**
 * Dedicated company-registration page. The panel empty state and the panel header link here
 * so registration is its own explained page rather than a bare form (requirement: company
 * registration is a page with title, description, hints, and steps).
 */
export default function NewCompanyPage() {
  return <CompanyRegistrationPage />;
}

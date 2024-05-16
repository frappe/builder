// Placed in separate file to setup frappe resource fetcher before loading the app.
import { frappeRequest, setConfig } from "frappe-ui";
setConfig("resourceFetcher", frappeRequest);

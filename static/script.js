function openReportForm(status) {
    document.getElementById("status").value = status;

    const handoverSection = document.getElementById("handover-section");

    if (status === "found") {
        handoverSection.style.display = "block";
    } else {
        handoverSection.style.display = "none";
    }

    document.getElementById("report-section").scrollIntoView({
        behavior: "smooth"
    });
}
// PASTE THE NEW FUNCTION HERE
function displayMatchingItems(matches) {
    const container = document.getElementById("item-container");

    container.innerHTML = "<h2>Matching Lost Items</h2>";

    matches.forEach(function(item) {
        const card = document.createElement("div");
        card.className = "item-card";

        const name = document.createElement("h3");
        name.textContent = item.item_name;

        const description = document.createElement("p");
        description.textContent = item.description;

        const location = document.createElement("p");
        location.textContent = "Lost Location: " + item.location;

        const reportId = document.createElement("p");
        reportId.textContent = "Report ID: #" + item.id;

        const requestButton = document.createElement("button");
        requestButton.textContent = "I Found This";
        requestButton.className = "details-button";
        requestButton.type = "button";

        requestButton.addEventListener("click", function() {
            openClaimRequestForm(item.id);
        });

        card.appendChild(name);
        card.appendChild(description);
        card.appendChild(location);
        card.appendChild(reportId);
        card.appendChild(requestButton);

        container.appendChild(card);
    });
}


function openClaimRequestForm(reportId) {

    // Show the claim request section
    const section = document.getElementById("claim-request-section");
    section.style.display = "block";

    // Store the lost item report ID in the hidden input
    document.getElementById("claim-report-id").value = reportId;

    // Scroll to the claim request form
    section.scrollIntoView({
        behavior: "smooth"
    });

}

const claimForm = document.getElementById("claim-request-form");

claimForm.addEventListener("submit", async function(event) {

    event.preventDefault();

    const reportId = document.getElementById("claim-report-id").value;

    const formData = new FormData(claimForm);

    try {

        const response = await fetch(`/send_request/${reportId}`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Failed to submit claim request");
        }

        alert("Claim request submitted successfully!");

        claimForm.reset();

        document.getElementById("claim-request-section").style.display = "none";

    } catch (error) {

        alert("Error: " + error.message);

        console.error("Claim request error:", error);

    }

});



// Submit a report to FastAPI
const reportForm = document.getElementById("report-form");

reportForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const formData = new FormData(reportForm);
    try {
        const response = await fetch("/report_item", {
            method: "POST",
            body: formData
        });

        // Read the response before using its data
        const result = await response.json();

        // Handle duplicate submissions
        if (response.status === 409) {
            alert(
                "This report already exists! Please check your previous report."
            );
            return;
        }

        // Handle other errors
        if (!response.ok) {
            throw new Error(
                result.detail || "Failed to submit report"
            );
        }

        // Successful submission
        let message = "Report submitted successfully!";

        // Display matching lost items for a found report
        
        if (formData.get("status") === "found") {
            const matches = result.matching_lost_items || [];

            if (matches.length > 0) {
                alert("Report submitted successfully! Matching lost items are available below.");
                displayMatchingItems(matches);
            } else {
                alert("Report submitted successfully! No matching lost items found.");
            }
        } else {
            alert("Report submitted successfully!");
        }


        // Clear the form
        reportForm.reset();

        // Refresh homepage cards
        if (formData.get("status") === "lost") {
        await loadReports();
}
    } catch (error) {
        alert("Error: " + error.message);
        console.error("Report submission error:", error);
    }
});

let allReports = []; // Store all reports for search functionality
// Load reports from FastAPI and display them
async function loadReports(reportsToDisplay = null)  {
    const container = document.getElementById("item-container");

    if (!container) {
        console.error("Item container not found in index.html");
        return;
    }

    try {
        let reports;

        if (reportsToDisplay === null) {
            const response = await fetch("/report_items");

            if (!response.ok) {
                throw new Error("Could not load reports");
            }

            allReports = await response.json();
            reports = allReports;

        } else {
            reports = reportsToDisplay;
        }

        container.innerHTML = "";

        if (reports.length === 0) {

            if (reportsToDisplay === null) {
                container.textContent = "No reports available yet.";
            } else {
                container.textContent = "No matching reports found.";
            }

            return;
        }

        reports.forEach(function(report) {
            // Create report card
            const card = document.createElement("div");
            card.className = "item-card";


            // Item image
            if (report.image_path) {
                const image = document.createElement("img");

                image.src = "/uploads/" + report.image_path;
                image.alt = report.item_name;
                image.className = "item-image";

                card.appendChild(image);
            }

            // Item name
            const name = document.createElement("h3");
            name.textContent = report.item_name;

            // Description
            const description = document.createElement("p");
            description.textContent = report.description;

            // Location
            const location = document.createElement("p");
            location.textContent = "Location: " + report.location;

            // Report ID
            const reportId = document.createElement("p");
            reportId.textContent = "Report ID: #" + report.id;

            // Reported date
            const reportDate = document.createElement("p");

            if (report.created_at) {
                const date = new Date(report.created_at);

                reportDate.textContent = "Reported: " +
                    (isNaN(date.getTime())
                        ? report.created_at
                        : date.toLocaleDateString());
            } else {
                reportDate.textContent = "Reported date unavailable";
            }

            // Status label
            const status = document.createElement("span");
            status.textContent = report.status;

            status.className =
                report.status === "lost"
                    ? "lost-label"
                    : "found-label";

            // Add information to card
            card.appendChild(name);
            card.appendChild(description);
            card.appendChild(location);
            card.appendChild(reportId);
            card.appendChild(reportDate);
            card.appendChild(status);

            // Create View Details button
            const detailsButton = document.createElement("button");

            detailsButton.textContent = "View Details";
            detailsButton.className = "details-button";
            detailsButton.type = "button";

            detailsButton.addEventListener("click", function() {
                viewReportDetails(report.id);
            });

            card.appendChild(detailsButton);

            // Add card to homepage
            container.appendChild(card);
        });

    } catch (error) {
        container.textContent =
            "Error loading reports. Please try again.";

        console.error("Error loading reports:", error);
    }
}


// View complete report details
async function viewReportDetails(reportId) {
    try {
        const response = await fetch(`/report_items/${reportId}`);

        if (!response.ok) {
            throw new Error("Could not load report details");
        }

        const report = await response.json();

        alert(
            "Item: " + report.item_name +
            "\nDescription: " + report.description +
            "\nLocation: " + report.location +
            "\nStatus: " + report.status.toUpperCase() +
            "\nReport ID: #" + report.id +
            "\nReported: " + (
                report.created_at
                    ? new Date(report.created_at).toLocaleString()
                    : "Unavailable"
            )
        );

    } catch (error) {
        console.error("Error loading report details:", error);
        alert(error.message);
    }
}
// Get the search input
const searchInput = document.getElementById("search-input");

// Get the status filter
const statusFilter = document.getElementById("status-filter");
// Get the search input
function applyFilters() {

    const searchText = searchInput.value.toLowerCase().trim();
    const selectedStatus = statusFilter.value;

    const filteredReports = allReports.filter(function(report) {

        const matchesSearch = report.item_name
            .toLowerCase()
            .includes(searchText);

        const matchesStatus =
            selectedStatus === "all" ||
            report.status === selectedStatus;

        return matchesSearch && matchesStatus;
    });

    loadReports(filteredReports);
}


// ADD EVENT LISTENERS HERE
searchInput.addEventListener("input", applyFilters);
statusFilter.addEventListener("change", applyFilters);


// Load reports when the page opens

loadReports(); // Load reports on page load





// Load reports from FastAPI and display them
async function loadReports(reportsToDisplay = null) {

    const container = document.getElementById("item-container");

    if (!container) {
        console.error("Item container not found in index.html");
        return;
    }

    try {
        let reports;

        if (reportsToDisplay === null) {
            const response = await fetch("/report_items");

            if (!response.ok) {
                throw new Error("Could not load reports");
            }

            allReports = await response.json();
            reports = allReports;

        } else {
            reports = reportsToDisplay;
        }

        container.innerHTML = "";

        if (reports.length === 0) {
            if (reportsToDisplay === null) {
                container.textContent = "No reports available yet.";
            } else {
                container.textContent = "No matching reports found.";
            }

            return;
        }

        reports.forEach(function(report) {

            // Create report card
            const card = document.createElement("div");
            card.className = "item-card";

            // Item image
            if (report.image_path) {
                const image = document.createElement("img");

                image.src = "/uploads/" + report.image_path;
                image.alt = report.item_name;
                image.className = "item-image";

                card.appendChild(image);
            }

            // Item name
            const name = document.createElement("h3");
            name.textContent = report.item_name;

            // Description
            const description = document.createElement("p");
            description.textContent = report.description;

            // Location
            const location = document.createElement("p");
            location.textContent = "Location: " + report.location;

            // Report ID
            const reportId = document.createElement("p");
            reportId.textContent = "Report ID: #" + report.id;

            // Reported date
            const reportDate = document.createElement("p");

            if (report.created_at) {
                const date = new Date(report.created_at);

                reportDate.textContent = "Reported: " +
                    (isNaN(date.getTime())
                        ? report.created_at
                        : date.toLocaleDateString());
            } else {
                reportDate.textContent = "Reported date unavailable";
            }

            // Status label
            const status = document.createElement("span");

            status.textContent = report.status;

            status.className =
                report.status === "lost"
                    ? "lost-label"
                    : "found-label";

            // Add information to card
            card.appendChild(name);
            card.appendChild(description);
            card.appendChild(location);
            card.appendChild(reportId);
            card.appendChild(reportDate);
            card.appendChild(status);

            // View Details button
            const detailsButton = document.createElement("button");

            detailsButton.textContent = "View Details";
            detailsButton.className = "details-button";
            detailsButton.type = "button";

            detailsButton.addEventListener("click", function() {
                viewReportDetails(report.id);
            });

            card.appendChild(detailsButton);

            // View Requests button (only for Lost Items)
            if (report.status === "lost") {

                const requestsButton = document.createElement("button");

                requestsButton.textContent = "View Requests";
                requestsButton.className = "details-button";
                requestsButton.type = "button";

                requestsButton.addEventListener("click", function() {
                    viewClaimRequests(report.id);
                });

                card.appendChild(requestsButton);
            }

            // Add card to homepage
            container.appendChild(card);

        });

    } catch (error) {

        container.textContent =
            "Error loading reports. Please try again.";

        console.error("Error loading reports:", error);
    }
}

async function viewClaimRequests(reportId) {
    const section = document.getElementById("owner-requests-section");
    const container = document.getElementById("owner-requests-container");

    section.style.display = "block";
    container.innerHTML = "<p>Loading requests...</p>";

    section.scrollIntoView({
        behavior: "smooth"
    });

    try {
        const response = await fetch(`/requests/${reportId}`);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Could not load requests");
        }

        container.innerHTML = "";

        if (result.requests.length === 0) {
            container.textContent = "No claim requests received yet.";
            return;
        }

        result.requests.forEach(function(request) {
            const card = document.createElement("div");
            card.className = "item-card";

            const title = document.createElement("h3");
            title.textContent = "Claim Request #" + request.id;

            const foundLocation = document.createElement("p");
            foundLocation.textContent = "Found Location: " + request.found_location;

            const foundTime = document.createElement("p");
            foundTime.textContent = "Found Time: " + (request.found_time || "Not provided");

            const currentLocation = document.createElement("p");
            currentLocation.textContent = "Current Location: " + (request.current_location || "Not provided");

            const description = document.createElement("p");
            description.textContent = "Description: " + request.description;

            const handover = document.createElement("p");
            handover.textContent = "Handover: " + request.handover_option;

            const status = document.createElement("p");
            status.textContent = "Status: " + request.status;

            card.appendChild(title);
            card.appendChild(foundLocation);
            card.appendChild(foundTime);
            card.appendChild(currentLocation);
            card.appendChild(description);
            card.appendChild(handover);
            card.appendChild(status);

            // Accept and Reject buttons
            if (request.status === "pending") {

                const acceptButton = document.createElement("button");
                acceptButton.textContent = "Accept";
                acceptButton.className = "accept-btn";

                acceptButton.onclick = function() {
                    updateClaimRequest(request.id, "accept", reportId);
                };

                const rejectButton = document.createElement("button");
                rejectButton.textContent = "Reject";
                rejectButton.className = "reject-btn";

                rejectButton.onclick = function() {
                    updateClaimRequest(request.id, "reject", reportId);
                };

                card.appendChild(acceptButton);
                card.appendChild(rejectButton);
            }

            container.appendChild(card);
        });

    } catch (error) {
        container.textContent = "Error loading claim requests.";
        console.error("Claim request error:", error);
    }
}


// Accept or Reject a claim request
async function updateClaimRequest(requestId, action, reportId) {

    const confirmation = confirm(
        `Are you sure you want to ${action} this claim request?`
    );

    if (!confirmation) {
        return;
    }

    try {
        const response = await fetch(
            `/requests/${requestId}/${action}`,
            {
                method: "PUT"
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Failed to update request");
        }

        alert(result.message);

        // Reload claim requests
        await viewClaimRequests(reportId);

        // Refresh lost and found reports
        await loadReports();

    } catch (error) {
        alert("Error: " + error.message);
        console.error("Update request error:", error);
    }
}

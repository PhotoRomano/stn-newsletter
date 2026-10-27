// Deploy as Web App (Execute as: Me, Who has access: Anyone).
// The resulting /exec URL is what all sign-up forms POST to.

const SHEET_ID = '1wAKlKyWzOQsbK4DU6BzvvGuWeBnnfdjWFtqM_ITE5jk';
const NOTIFY_EMAIL = 'stnicholas.soc@gmail.com';

const FORMS = {
  'Church School': {
    tab: 'Church School Sign-Ups',
    headers: ['Timestamp', 'Student First Name', 'Student Last Name', 'Student Age', 'Grade',
      'Parent First Name', 'Parent Last Name', 'Parent Email', 'Parent Phone', 'Siblings', 'Notes'],
    row: function (p) {
      return [new Date(), p['Student First Name'], p['Student Last Name'], p['Student Age'], p['Grade'] || '',
        p['Parent First Name'], p['Parent Last Name'], p['Parent Email'], p['Parent Phone'],
        p['Siblings'] || '', p['Notes'] || ''];
    },
    nameCols: [1, 2]
  },
  'Serbian School': {
    tab: 'Serbian School Sign-Ups',
    headers: ['Timestamp', 'Student First Name', 'Student Last Name', 'Student Age', 'Serbian Level',
      'Parent First Name', 'Parent Last Name', 'Parent Email', 'Parent Phone', 'Siblings', 'Notes'],
    row: function (p) {
      return [new Date(), p['Student First Name'], p['Student Last Name'], p['Student Age'], p['Serbian Level'] || '',
        p['Parent First Name'], p['Parent Last Name'], p['Parent Email'], p['Parent Phone'],
        p['Siblings'] || '', p['Notes'] || ''];
    },
    nameCols: [1, 2]
  },
  'Young Adults': {
    // NOTE 2026-10-27: sheet tab renamed from the old "Teens" labeling to
    // "Member"/"Parent-Guardian" to match the Young Adults rebrand (this
    // form spans both teens and adults -- see the newsletter's own Young
    // Adults section copy, "a few teens and young adults"). `headers` only
    // controls the label text written to a BRAND NEW sheet's row 1
    // (getOrCreateSheet only writes headers once, on creation) -- the
    // live "Young Adults Sign-Ups" tab's row 1 was updated to match by
    // hand the same day, via the Sheets API, touching no data rows.
    // `row()`'s p['Teen ...'] keys below are the HTML form's actual field
    // names on the live site and are intentionally UNCHANGED -- renaming
    // those would require also updating the live form's input `name`
    // attributes, a bigger/riskier change out of scope for this cleanup.
    tab: 'Young Adults Sign-Ups',
    headers: ['Timestamp', 'Member First Name', 'Member Last Name', 'Member Age', 'Member Contact',
      'Parent/Guardian First Name', 'Parent/Guardian Last Name', 'Parent/Guardian Email', 'Parent/Guardian Phone',
      'Interested in Leading', 'Activity or Volunteer Idea', 'Notes'],
    row: function (p) {
      return [new Date(), p['Teen First Name'], p['Teen Last Name'], p['Teen Age'], p['Teen Contact'] || '',
        p['Parent First Name'], p['Parent Last Name'], p['Parent Email'], p['Parent Phone'],
        p['Interested in Leading'] || '', p['Activity or Volunteer Idea'] || '', p['Notes'] || ''];
    },
    nameCols: [1, 2]
  },
  'SerbFest Volunteer': {
    tab: 'SerbFest Volunteers',
    headers: ['Timestamp', 'First Name', 'Last Name', 'Email', 'Phone',
      'Friday Setup', 'Saturday', 'Sunday',
      'Kitchen Prep & Cooking', 'Grill/Roasting', 'Tent Setup/Breakdown',
      'Serving/Cashier', 'Cleaning', 'Kids Zone Supervision', 'Yard/Grounds Work',
      'Wherever Needed', 'Notes'],
    row: function (p) {
      return [new Date(), p['First Name'], p['Last Name'], p['Email'], p['Phone'],
        p['Friday Setup'] || '', p['Saturday'] || '', p['Sunday'] || '',
        p['Kitchen Prep & Cooking'] || '', p['Grill/Roasting'] || '', p['Tent Setup/Breakdown'] || '',
        p['Serving/Cashier'] || '', p['Cleaning'] || '', p['Kids Zone Supervision'] || '',
        p['Yard/Grounds Work'] || '', p['Wherever Needed'] || '', p['Notes'] || ''];
    },
    nameCols: [1, 2]
  },
  'Cookie and Cake': {
    tab: 'Cookie and Cake Sign-Ups',
    headers: ['Timestamp', 'First Name', 'Last Name', 'Email', 'Phone',
      'Baking - What/How Much', 'Baking - Drop-off', 'Staffing - Shift', 'Notes'],
    row: function (p) {
      return [new Date(), p['First Name'], p['Last Name'], p['Email'], p['Phone'],
        p['Baking What'] || '', p['Baking Drop-off'] || '', p['Staffing Shift'] || '', p['Notes'] || ''];
    },
    nameCols: [1, 2]
  }
};

function getOrCreateSheet(name, headerRow) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headerRow);
  }
  return sheet;
}

function doPost(e) {
  var p = e.parameter;
  var formName = p['_form'] || 'Unknown';
  var form = FORMS[formName];

  if (!form) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: 'Unknown form: ' + formName }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var row = form.row(p);
  getOrCreateSheet(form.tab, form.headers).appendRow(row);

  var name = form.nameCols.map(function (i) { return row[i]; }).join(' ');
  notify(formName, name, row);

  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}

// Run this once manually from the Apps Script editor (select "setupSheets" in the
// function dropdown, click Run) to create all 5 tabs with their headers right away,
// instead of waiting for each form's first real submission.
function setupSheets() {
  Object.keys(FORMS).forEach(function (formName) {
    var form = FORMS[formName];
    getOrCreateSheet(form.tab, form.headers);
  });
}

function notify(formName, name, row) {
  try {
    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: formName + ' Sign-Up: ' + name,
      body: 'New sign-up received:\n\n' + row.join('\n')
    });
  } catch (err) {
    // don't fail the request just because the notification email hiccuped
  }
}

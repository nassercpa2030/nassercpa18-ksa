<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- ============================= -->
    <!-- Report Action -->
    <!-- ============================= -->
    <record id="action_quality_customer_report" model="ir.actions.report">
        <field name="name">نموذج بيانات العميل</field>
        <field name="model">sale.order</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">kbi_custom.quality_customer_report</field>
        <field name="print_report_name">f"بينات العميل-{object.partner_id.name or ''} - لأمر البيع- {object.name or ''} "</field>
        <field name="paperformat_id" ref="kbi_custom.paperformat_zero_margin"/>
        <field name="binding_model_id" ref="sale.model_sale_order"/>
        <field name="binding_type">report</field>
    </record>

    <!-- ============================= -->
    <!-- QWEB REPORT -->
    <!-- ============================= -->
    <template id="quality_customer_report">
        <t t-foreach="docs" t-as="o">
            <t t-call="kbi_custom.external_layout_seti">

                <!-- ======================= -->
                <!-- Body CSS only -->
                <!-- ======================= -->
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&amp;display=swap');

                    /* CSS يطبق فقط على محتوى التقرير */
                    .report-body, 
                    .report-body table, 
                    .report-body td, 
                    .report-body th { 
                        font-family: 'Tajawal', sans-serif; 
                        font-size: 13px; 
                    }

                    .report-body th { 
                        font-weight: bold; 
                        font-size: 13.5px; 
                        background:#EAF3FF; 
                    }

                    .report-body table { 
                        width: 100%; 
                        border-collapse: collapse; 
                    }

                    .report-body td, .report-body th { 
                        padding:5px; 
                        border:1px solid #2F6FB2; 
                        text-align:right; 
                        vertical-align:middle; 
                    }

                    .report-body .thank-you { 
                        text-align:center; 
                        font-size:12px; 
                        color:#2F6FB2; 
                    }

                    .report-body .decor { 
                        color:#c71585; 
                        margin-top:5px; 
                        letter-spacing:2px; 
                    }

                    .report-body .header-title2 { 
                        font-size:18px; 
                        text-align:center; 
                        font-weight:bold; 
                        margin-bottom:10px;  
                        padding-top:6px;
                    }

                    .report-body .signature-cell { 
                        width:45%; 
                        text-align:center; 
                        vertical-align:middle; 
                    }

                    .report-body strong { 
                        display:block; 
                        text-align:center; 
                    }
                    .signature-images img {
                        display: block;
                        height: 55px;
                        max-width: 25%;
                        margin: 0 auto;
                        padding: 0;
                        border: 0;
                    }
   
                </style>

                <!-- ======================= -->
                <!-- Body Content -->
                <!-- ======================= -->
                <div class="page report-body" style="margin:0;padding:0 0 180px 0;">

                    <!-- عنوان التقرير -->
                    <div class="header-title2">تقـريــر بيــانـات  العمــــيل</div>

                    <table style="margin-top:12px;">
                        <tr>
                            <td width="100%">
                                <table width="100%" style="border-collapse:collapse;">
                                      <!-- <t t-set="bg_colors" t-value="['#e6f2ff', '#cce6ff', '#b3d9ff', '#99ccff', '#cce0e6', '#e6e6e6']"/>

                                     <t t-set="color" t-value="bg_colors[(pay_index-1) % len(bg_colors)]"/> -->

                                    <tr>
                                        <td><strong>رقم أمر البيع</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.name or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Sale Order No</strong></td>
                                    </tr>
                                   <tr>
                                        <td><strong>الخدمة المقدمة </strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.project_name or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Provided Service</strong></td>
                                    </tr>
                                    <tr>
                                    <td><strong> ســنة الخدمة المقدمة </strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.account_year or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Provided Service Year</strong></td>
                                    </tr>

                                    <tr>
                                        <td><strong> تاريخ طلب العــقد</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.date_order or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Order Date</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>أســم العميل  </strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.name or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Customer Name</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>رقم الســجل التــجاري </strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.cr_number_sale or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Commercial Registration Number</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>الرقـــم  الــموحــد</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.number_700 or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Tax Number</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>الرقـــم الـضــريبي</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.partner_vat_placeholder or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Unified(700)Number</strong></td>
                                    </tr>

                                    <tr>
                                        <td><strong>الرقــم الأرضــي</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.leadline or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Landline Number</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>الإيمــــيل</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.email or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Email</strong></td>
                                    </tr>
                                     <tr>
                                        <td><strong>أســـم الشخص المفوض بالتواصل</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.financial_manager_name or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Authorized Contact Person Name</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>رقــم الــموبايــل</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.partner_id.mobile or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Mobile number</strong></td>
                                    </tr>
                                     <tr>
                                        <td><strong>أســـم مــديــر المــجــمــوعــة</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.user_id or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Group Manager Name</strong></td>
                                    </tr>
                                     <tr>
                                        <td><strong>رقــم الــمجــموعـــة</strong></td>
                                        <td style="text-align:center;"><strong><span t-esc="o.team_id or '-'"/></strong></td>
                                        <td style="text-align:left;"><strong>Group Number</strong></td>
                                    </tr>

                                </table>
                            </td>
                        </tr>
                    </table>

                    <!-- شكر ودعم نهائي -->
                    <div class="thank-you" style="margin-top:40px; text-align:center; font-size:12px; line-height:1.4;">
                        <strong>🌸🌸🌸 نشكر لكم ثقتكم باستخدام نظام أودوو 🌸🌸🌸</strong>
                        <div class="decor" style="margin:5px 0;">
                            ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀ ❀
                        </div>
                        <p style="margin-top:5px; font-size:11px; font-style:italic;">
                            مقدم من إدارة الدعم الفني بشركة 
                            <strong>ناصر عوض أل كيرعان – محاسبون ومراجعون قانونيون</strong>، متمنين لكم دوام التميز والرقي.
                        </p>
                    </div>

                </div>
            </t>
        </t>
    </template>
</odoo>
